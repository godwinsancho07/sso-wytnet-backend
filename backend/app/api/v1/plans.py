from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from app.db.session import get_db
from app.models.plan import Plan, PlanType, CreditLog
from app.models.oauth_client import OAuthClient
from app.models.user import User
from app.schemas.plan import (
    PlanCreate, PlanUpdate, PlanResponse, PlanStats, CreditLogResponse,
    RazorpayOrderResponse, RazorpayVerification
)
from app.api.deps import get_current_superuser, CurrentUser, get_client_ip
from app.models.role import Role, UserRole
from app.config import settings
import os
import logging
import hmac
import hashlib
import httpx

logger = logging.getLogger(__name__)

router = APIRouter()

print("!!! PLANS ROUTER LOADING !!!")

@router.get("", response_model=List[PlanResponse])
async def list_plans(
    plan_type: Optional[PlanType] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    query = select(Plan)
    if plan_type:
        query = query.where(Plan.type == plan_type)
    
    plans = (await db.execute(query)).scalars().all()
    
    # Auto-seed Developer Plans if missing
    if plan_type == PlanType.DEVELOPER and len(plans) < 2:
        # Ensure Free exists
        if not any(p.name == "Free" for p in plans):
            free = Plan(
                name="Free", type=PlanType.DEVELOPER, price=0.0,
                description="Default developer plan - 2 login credits",
                is_default=True, is_active=True, credits_limit=2,
                app_registrations_limit=0
            )
            db.add(free)
            
        # Ensure Unlimited exists
        if not any(p.name == "Unlimited" for p in plans):
            unlimited = Plan(
                name="Unlimited", type=PlanType.DEVELOPER, price=1.0,
                description="Unlimited users and app registrations for lifetime",
                is_default=False, is_active=True, credits_limit=0,
                app_registrations_limit=0
            )
            db.add(unlimited)
        await db.commit()
        # Re-fetch
        plans = (await db.execute(query)).scalars().all()
        
    return plans

@router.get("/available", response_model=List[PlanResponse])
async def get_available_plans(
    current_user: CurrentUser,
    plan_type: Optional[PlanType] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Plan).where(Plan.is_active == True)
    if plan_type:
        query = query.where(Plan.type == plan_type)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/public", response_model=List[PlanResponse])
async def get_public_plans(
    plan_type: Optional[PlanType] = None,
    db: AsyncSession = Depends(get_db)
):
    """Publicly accessible list of active plans."""
    # Direct database override to ensure plans have correct prices
    from sqlalchemy import text
    try:
        await db.execute(text("UPDATE plans SET price = 1.0 WHERE (name = 'Growth' or name = 'growth') and type = 'DEVELOPER'"))
        await db.execute(text("UPDATE plans SET price = 2.0 WHERE (name = 'Pro' or name = 'pro') and type = 'DEVELOPER'"))
        await db.commit()
    except Exception as sql_err:
        logger.error(f"Direct SQL update failed: {str(sql_err)}")

    # Delete legacy Pro user plan if it exists
    res = await db.execute(
        select(Plan).where(
            Plan.type == PlanType.USER,
            (Plan.name == "Pro") | (Plan.name == "Pro Plan") | (Plan.name.ilike("%pro%"))
        )
    )
    pro_user_plans = res.scalars().all()
    for p in pro_user_plans:
        await db.delete(p)
    if pro_user_plans:
        await db.commit()

    # Sync Developer Plans to match WytSaaS Marketplace (Starter, Growth, Pro)
    if plan_type == PlanType.DEVELOPER or plan_type is None:
        res = await db.execute(select(Plan).where(Plan.type == PlanType.DEVELOPER))
        dev_plans = res.scalars().all()
        
        starter = next((p for p in dev_plans if p.name.lower() in ["starter", "free"]), None)
        growth = next((p for p in dev_plans if p.name.lower() in ["growth", "growth plan"]), None)
        pro = next((p for p in dev_plans if p.name.lower() in ["pro", "unlimited", "pro plan"]), None)
        
        # Force update Starter
        if starter:
            starter.name = "Starter"
            starter.app_registrations_limit = 1
            starter.price = 0.0
            starter.description = "1 Hosted App, 1,000 Users Limit"
        else:
            starter = Plan(name="Starter", type=PlanType.DEVELOPER, price=0.0, description="1 Hosted App, 1,000 Users Limit", app_registrations_limit=1, is_default=True, is_active=True)
            db.add(starter)
            
        # Force update Growth
        if growth:
            growth.name = "Growth"
            growth.app_registrations_limit = 5
            growth.price = 1.0
            growth.description = "5 Hosted Apps, 10,000 Users Limit"
        else:
            growth = Plan(name="Growth", type=PlanType.DEVELOPER, price=1.0, description="5 Hosted Apps, 10,000 Users Limit", app_registrations_limit=5, is_default=False, is_active=True)
            db.add(growth)
            
        # Force update Pro
        if pro:
            pro.name = "Pro"
            pro.app_registrations_limit = 0
            pro.price = 2.0
            pro.description = "Unlimited Apps, Unlimited Users"
        else:
            pro = Plan(name="Pro", type=PlanType.DEVELOPER, price=2.0, description="Unlimited Apps, Unlimited Users", app_registrations_limit=0, is_default=False, is_active=True)
            db.add(pro)

        # Flush session to assign IDs to new plans before delete check
        await db.flush()

        # Delete any other developer plans
        valid_ids = [p.id for p in [starter, growth, pro] if p]
        for p in dev_plans:
            if p.id not in valid_ids:
                await db.delete(p)

        await db.commit()

    query = select(Plan).where(Plan.is_active == True)
    if plan_type:
        query = query.where(Plan.type == plan_type)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/my-plan", response_model=Optional[PlanResponse])
async def get_my_plan(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    if not current_user.plan_id:
        return None
    return await db.get(Plan, current_user.plan_id)

@router.get("/credit-logs", response_model=List[CreditLogResponse])
async def get_credit_logs(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
):
    query = (
        select(CreditLog)
        .where(CreditLog.owner_id == current_user.id)
        .order_by(CreditLog.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/stats", response_model=PlanStats)
async def get_plan_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    developer_plans = await db.scalar(select(func.count(Plan.id)).where(Plan.type == PlanType.DEVELOPER))
    user_plans = await db.scalar(select(func.count(Plan.id)).where(Plan.type == PlanType.USER))
    active_apps = await db.scalar(select(func.count(OAuthClient.id)).where(OAuthClient.is_active == True))
    total_users = await db.scalar(select(func.count(User.id)))
    
    # Calculate Revenue from CreditLogs
    # Every 'plan_upgrade' event in our simulation costs ₹1
    total_upgrades = await db.scalar(
        select(func.count(CreditLog.id))
        .where(CreditLog.event_type == "plan_upgrade")
    ) or 0
    
    from datetime import datetime, time, timezone
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_upgrades = await db.scalar(
        select(func.count(CreditLog.id))
        .where(CreditLog.event_type == "plan_upgrade", CreditLog.created_at >= today_start)
    ) or 0
    
    return PlanStats(
        developer_plans_count=developer_plans or 0,
        user_plans_count=user_plans or 0,
        active_developer_apps_count=active_apps or 0,
        total_enrolled_users_count=total_users or 0,
        total_revenue=float(total_upgrades),
        today_revenue=float(today_upgrades),
        total_upgrades=total_upgrades
    )

@router.post("/create-razorpay-order", response_model=RazorpayOrderResponse)
async def create_razorpay_order(
    plan_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    plan = await db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    if plan.price <= 0:
        raise HTTPException(status_code=400, detail="This plan is free")

    # Amount in paise (multiply by 100)
    amount = int(plan.price * 100)
    
    data = {
        "amount": amount,
        "currency": "INR",
        "receipt": f"receipt_{current_user.id[:8]}_{int(datetime.now().timestamp())}",
    }
    
    try:
        url = "https://api.razorpay.com/v1/orders"
        with httpx.Client() as client:
            response = client.post(
                url,
                json=data,
                auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
            )
            response.raise_for_status()
            order = response.json()
        return {
            "order_id": order['id'],
            "amount": amount,
            "currency": "INR",
            "key_id": settings.razorpay_key_id
        }
    except Exception as e:
        logger.error(f"Razorpay Order Creation Failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create Razorpay order: {str(e)}")

@router.post("/verify-razorpay-payment")
async def verify_razorpay_payment(
    request: Request,
    verification: RazorpayVerification,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    # Verify signature natively
    try:
        msg = f"{verification.razorpay_order_id}|{verification.razorpay_payment_id}"
        generated_signature = hmac.new(
            settings.razorpay_key_secret.encode('utf-8'),
            msg.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(generated_signature, verification.razorpay_signature):
            raise HTTPException(status_code=400, detail="Invalid payment signature")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    # Get the plan
    plan = await db.get(Plan, verification.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if plan.type == PlanType.DEVELOPER and plan.name == "Unlimited":
        # BUY UNLIMITED LOGIC
        if verification.target_client_id:
            # Upgrade specific app
            stmt = select(OAuthClient).where(OAuthClient.id == verification.target_client_id)
            client_obj = (await db.execute(stmt)).scalar_one_or_none()
            if client_obj:
                client_obj.plan_id = plan.id
                desc = f"Upgraded {client_obj.app_name} to Unlimited (Paid ₹{plan.price})"
            else:
                desc = f"Upgraded account to Unlimited (Paid ₹{plan.price})"
                current_user.plan_id = plan.id
        else:
            # Upgrade whole account
            current_user.plan_id = plan.id
            desc = f"Upgraded account to Unlimited (Paid ₹{plan.price})"
            
            # Update all apps owned by user
            from app.models.client_admin import ClientAdmin
            admin_stmt = select(ClientAdmin.client_id).where(ClientAdmin.user_id == current_user.id)
            client_ids = (await db.execute(admin_stmt)).scalars().all()
            if client_ids:
                await db.execute(
                    update(OAuthClient)
                    .where(OAuthClient.id.in_(client_ids))
                    .values(plan_id=plan.id)
                )

        log = CreditLog(
            owner_id=current_user.id,
            event_type="plan_upgrade",
            description=f"{desc} - Razorpay: {verification.razorpay_payment_id}",
            credits_change=0
        )
        db.add(log)
    elif plan.type == PlanType.USER:
        current_user.plan_id = plan.id
        desc = f"Upgraded user subscription to {plan.name} (Paid ₹{plan.price})"
        log = CreditLog(
            owner_id=current_user.id,
            event_type="plan_upgrade",
            description=f"{desc} - Razorpay: {verification.razorpay_payment_id}",
            credits_change=0
        )
        db.add(log)

    # General audit log
    from app.repositories.audit_log import AuditLogRepository
    audit_repo = AuditLogRepository(db)
    await audit_repo.create(
        user_id=current_user.id,
        event_type="plan_upgrade",
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={
            "plan": plan.name,
            "price": plan.price,
            "payment_id": verification.razorpay_payment_id,
            "order_id": verification.razorpay_order_id
        }
    )

    await db.commit()
    return {"status": "success", "message": f"Successfully upgraded to {plan.name}"}

@router.post("", response_model=PlanResponse)
async def create_plan(
    plan_in: PlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    # If this is the default plan, unset other defaults of the same type
    if plan_in.is_default:
        await db.execute(
            update(Plan)
            .where(Plan.type == plan_in.type, Plan.is_default == True)
            .values(is_default=False)
        )
    
    db_plan = Plan(**plan_in.model_dump())
    db.add(db_plan)
    await db.commit()
    await db.refresh(db_plan)
    return db_plan

    return {
        "status": "success"
    }

@router.get("/debug/logs")
async def debug_logs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    types_stmt = select(CreditLog.event_type).distinct()
    types = (await db.execute(types_stmt)).scalars().all()
    
    recent_stmt = select(CreditLog).order_by(CreditLog.created_at.desc()).limit(10)
    recent = (await db.execute(recent_stmt)).scalars().all()
    recent_list = [{"type": l.event_type, "desc": l.description, "at": l.created_at.isoformat()} for l in recent]
    
    count_stmt = select(func.count(CreditLog.id))
    total_count = (await db.execute(count_stmt)).scalar()
    
    return {
        "event_types": types, 
        "total_logs": total_count,
        "recent_logs": recent_list,
        "count_all": total_count
    }

@router.post("/debug/simulate")
async def simulate_transaction(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    log = CreditLog(
        owner_id=current_user.id,
        event_type="plan_upgrade",
        description="SIMULATED: Plan Upgrade (₹1.00)",
        credits_change=0
    )
    db.add(log)
    await db.commit()
    return {"status": "success"}

@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    plan = await db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan

@router.patch("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: str,
    plan_in: PlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    db_plan = await db.get(Plan, plan_id)
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    update_data = plan_in.model_dump(exclude_unset=True)
    
    if update_data.get("is_default"):
        await db.execute(
            update(Plan)
            .where(Plan.type == db_plan.type, Plan.is_default == True)
            .values(is_default=False)
        )
    
    for field, value in update_data.items():
        setattr(db_plan, field, value)
    
    await db.commit()
    await db.refresh(db_plan)
    return db_plan

@router.post("/join-developer-program")
async def join_developer_program(
    request: Request,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    # 1. Get or create the default DEVELOPER plan (e.g. "Free")
    stmt = select(Plan).where(Plan.type == PlanType.DEVELOPER, Plan.is_default == True)
    dev_plan = (await db.execute(stmt)).scalar_one_or_none()
    
    if not dev_plan:
        # Fallback to any developer plan
        stmt = select(Plan).where(Plan.type == PlanType.DEVELOPER)
        dev_plan = (await db.execute(stmt)).scalars().first()
        
    if not dev_plan:
        # Create a basic Free developer plan if none exists
        dev_plan = Plan(
            name="Free",
            type=PlanType.DEVELOPER,
            price=0.0,
            description="Default developer plan",
            is_active=True,
            is_default=True,
            credits_limit=2,
            app_registrations_limit=0 # Unlimited
        )
        db.add(dev_plan)
        await db.flush()

    # 2. Update user's plan to the Developer plan
    current_user.plan_id = dev_plan.id

    # 3. Ensure user has app_admin role
    stmt = select(Role).where(Role.name == "app_admin")
    role = (await db.execute(stmt)).scalar_one_or_none()
    if not role:
        role = Role(name="app_admin", description="Application Administrator")
        db.add(role)
        await db.flush()
    
    # Check if they already have the role relationship
    role_stmt = select(UserRole).where(UserRole.user_id == current_user.id, UserRole.role_id == role.id)
    existing_role = (await db.execute(role_stmt)).scalar_one_or_none()
    
    if not existing_role:
        user_role = UserRole(user_id=current_user.id, role_id=role.id)
        db.add(user_role)

    # 4. Log the transaction
    log = CreditLog(
        owner_id=current_user.id,
        event_type="plan_upgrade",
        description="Joined Developer Program",
        credits_change=0
    )
    db.add(log)
    
    await db.commit()
    return {"status": "success", "message": "Welcome to the Developer Program!", "plan": dev_plan.name}

@router.post("/buy-unlimited")
async def buy_unlimited(
    request: Request,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    # 1. Ensure "Unlimited" plan exists
    stmt = select(Plan).where(Plan.name == "Unlimited", Plan.type == PlanType.DEVELOPER)
    unlimited_plan = (await db.execute(stmt)).scalar_one_or_none()
    
    if not unlimited_plan:
        unlimited_plan = Plan(
            name="Unlimited",
            type=PlanType.DEVELOPER,
            price=1.0,
            description="Unlimited users and app registrations for lifetime",
            credits_limit=0, # unlimited
            app_registrations_limit=0, # unlimited
            is_active=True,
            is_default=False
        )
        db.add(unlimited_plan)
        await db.flush()

    # 2. Update user's plan
    current_user.plan_id = unlimited_plan.id
    
    # 3. Update all apps owned by user to use this plan
    from app.models.client_admin import ClientAdmin
    admin_stmt = select(ClientAdmin.client_id).where(ClientAdmin.user_id == current_user.id)
    client_ids = (await db.execute(admin_stmt)).scalars().all()
    
    if client_ids:
        await db.execute(
            update(OAuthClient)
            .where(OAuthClient.id.in_(client_ids))
            .values(plan_id=unlimited_plan.id)
        )
    
    # 4. Log the purchase in CreditLog
    log = CreditLog(
        owner_id=current_user.id,
        event_type="plan_upgrade",
        description="Upgraded to Unlimited Plan (Paid ₹1)",
        credits_change=0
    )
    db.add(log)
    
    # 5. Log the purchase in AuditLog for visibility
    from app.repositories.audit_log import AuditLogRepository
    from app.api.deps import get_client_ip
    audit_repo = AuditLogRepository(db)
    await audit_repo.create(
        user_id=current_user.id,
        event_type="plan_upgrade",
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={"plan": "Unlimited", "price": 1.0}
    )
    
    await db.commit()
    return {"status": "success", "message": "Upgraded to Unlimited Plan", "plan": unlimited_plan.name}

@router.delete("/{plan_id}")
async def delete_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    db_plan = await db.get(Plan, plan_id)
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    if db_plan.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete default plan")
        
    await db.delete(db_plan)
    await db.commit()
    return {"message": "Plan deleted successfully"}
