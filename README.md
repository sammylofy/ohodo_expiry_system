# Design and Implementation of an Automated Product Expiry Alert System for Retail Stores
**A Case Study of Ohodo, Enugu State (National Diploma Project)**

## Overview
Retail stores in semi-urban communities such as **Ohodo in Igbo-Etiti LGA, Enugu State** frequently experience financial loss and public health hazards caused by unnoticed expired products on shelves. Manual stock inspection is slow, error-prone, and reactive.

This software provides a **proactive, automated expiry monitoring and multi-channel alert system** built with **Django 5**, **APScheduler**, **Termii API (SMS & WhatsApp)**, and **SMTP Email**.

---

## Key Features
1. **Dynamic Expiry Computation**: Every product batch automatically computes `days_to_expiry` and classifies stock into:
   - **Expired** (`< 0 days` — Red `bg-danger`)
   - **Critical** (`0–7 days` — Amber `bg-warning text-dark`)
   - **Warning** (`8–30 days` — Cyan `bg-info text-dark`)
   - **Safe** (`> 30 days` — Green `bg-success`)
2. **Multi-Channel Automated Alerts**:
   - Background cron job (`django-apscheduler`) runs daily at **08:00 AM (Africa/Lagos)** to inspect all in-stock items expiring within 30 days and dispatches **Email**, **Termii SMS**, and **Termii WhatsApp** notifications while recording an audit trail in `AlertLog`.
3. **FEFO Point-of-Sale (POS)**:
   - Lists available products ordered by earliest expiry date (*First-Expired, First-Out*) and prevents overselling beyond available stock.
4. **100% Responsive & Light/Dark Theme**:
   - Zero horizontal scroll from `320px` mobile screens up to `1024px+` desktops.
   - Product table automatically transforms into mobile cards below `768px`.

---

## Local Setup Instructions

```bash
# 1. Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env

# 4. Run database migrations
python manage.py makemigrations
python manage.py migrate

# 5. Create an admin/staff account
python manage.py createsuperuser

# 6. Run the development server
python manage.py runserver