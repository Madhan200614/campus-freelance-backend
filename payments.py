from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import Wallet, Transaction
from jobs import get_current_user
import razorpay
import os
from dotenv import load_dotenv

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

router = APIRouter(prefix="/payments", tags=["Payments"])

class AddMoneyRequest(BaseModel):
    amount: float

@router.post("/create-order")
def create_order(req: AddMoneyRequest, user_id: int = Depends(get_current_user)):
    amount_in_paise = int(req.amount * 100)
    order = client.order.create({
        "amount": amount_in_paise,
        "currency": "INR",
        "payment_capture": 1
    })
    return {
        "order_id": order["id"],
        "amount": req.amount,
        "currency": "INR",
        "key_id": RAZORPAY_KEY_ID
    }

@router.post("/verify")
def verify_payment(
    order_id: str,
    payment_id: str,
    signature: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        })
    except Exception:
        raise HTTPException(status_code=400, detail="Payment verification failed")

    # Get or create wallet
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if not wallet:
        wallet = Wallet(user_id=user_id, balance=0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

    # Get amount from order
    order = client.order.fetch(order_id)
    amount = order["amount"] / 100

    # Add to wallet
    wallet.balance += amount
    db.commit()

    # Save transaction
    transaction = Transaction(
        user_id=user_id,
        amount=amount,
        type="credit",
        description="Wallet top-up via Razorpay"
    )
    db.add(transaction)
    db.commit()

    return {"message": "Payment successful", "new_balance": wallet.balance}

@router.get("/wallet")
def get_wallet(db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if not wallet:
        return {"balance": 0}
    return {"balance": wallet.balance}

@router.get("/transactions")
def get_transactions(db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()
    return transactions