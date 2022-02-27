from pydantic import BaseModel, Field, EmailStr


class Address(BaseModel):
    country: str = Field(..., description="Country")
    state: str = Field(..., description="State")
    city: str = Field(..., description="City")
    street: str = Field(..., description="Street")
    zip: str = Field(..., description="Zip")


class CustomerSchema(BaseModel):
    account_holder_name: str = Field(..., description="Name of the Account holder")
    aadhaar: str = Field(..., description="Aadhaar number of the Account holder", max_length=12, min_length=12)
    pan: str = Field(..., description="PAN of the Account holder", max_length=10, min_length=10)
    contact: str = Field(..., description="Contact number of the Account holder", max_length=10, min_length=10)
    email: EmailStr = Field(..., description="Email ID of the Account holder")
    dob: str = Field(..., description="Date Of Birth of the Account holder")
    address: Address = Field(..., description="Address of the Account holer")


class AccountSchema:
    account_number: str = Field(..., description="Account Number")
    created_date: str = Field(..., description="Date on which account is created")
    branch_name: str = Field(..., description="Branch at which Account was created")
    ifsc_code: str = Field(..., description="IFSC code of the branch")
    bank_name: str = Field(..., description="Name of the Bank")
    account_type: str = Field(..., description="Type of an account - Savings/Current")
    aadhaar: str = Field(..., description="Aadhaar number of the Account holder")
    balance: int = Field(..., description="Account balance")
    last_activity: str = Field(..., description="Date of the latest activity performed by the user on his account")
    is_active: bool = Field(..., description="Account status")



