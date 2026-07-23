"""
Multi-tenant schema: one row in `businesses` per client you onboard.
Everything else (services, customers, messages, appointments) hangs off business_id.
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    whatsapp_phone_number_id = Column(String, unique=True, index=True)  # Meta's phone_number_id
    business_type = Column(String, default="general")  # clinic, salon, coaching, gym, ...
    reply_language = Column(String, default="hinglish")  # hinglish | english | hindi
    timezone = Column(String, default="Asia/Kolkata")
    open_time = Column(String, default="09:00")
    close_time = Column(String, default="19:00")
    working_days = Column(String, default="Mon,Tue,Wed,Thu,Fri,Sat")
    slot_duration_minutes = Column(Integer, default=30)
    created_at = Column(DateTime, default=datetime.utcnow)

    services = relationship("Service", back_populates="business", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="business", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="business", cascade="all, delete-orphan")


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    name = Column(String, nullable=False)  # "Root Canal", "Hair Spa", "Class 10 Math Tuition"
    price = Column(Float, default=0.0)
    duration_minutes = Column(Integer, default=30)
    description = Column(Text, default="")

    business = relationship("Business", back_populates="services")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    phone_number = Column(String, index=True)  # customer's WhatsApp number, E.164-ish
    name = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="customers")
    messages = relationship("Message", back_populates="customer", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="customer", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    role = Column(String)  # "user" or "assistant"
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="messages")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    customer_id = Column(Integer, ForeignKey("customers.id"))
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True)
    scheduled_at = Column(DateTime, nullable=False)
    status = Column(String, default="confirmed")  # confirmed | cancelled | completed
    reminder_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="appointments")
    customer = relationship("Customer", back_populates="appointments")
