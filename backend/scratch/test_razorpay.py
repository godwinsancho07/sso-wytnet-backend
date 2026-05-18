import os
import razorpay
from dotenv import load_dotenv

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_live_RMxf287wX4f7FQ")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "1MLyIthYIvhJ7MMNWRvZ2qRO")

print(f"Key ID: {RAZORPAY_KEY_ID}")
# Don't print the whole secret for security, just length and first/last
print(f"Key Secret Length: {len(RAZORPAY_KEY_SECRET)}")
print(f"Key Secret Starts with: {RAZORPAY_KEY_SECRET[:4]}")

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

data = {
    "amount": 10000, # ₹100
    "currency": "INR",
    "receipt": "test_receipt",
}

try:
    order = client.order.create(data=data)
    print("Order created successfully!")
    print(order)
except Exception as e:
    print(f"Error creating order: {str(e)}")
