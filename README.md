# Wulf's Routing Automation

Wulf's Routing Automation is a web-based tool designed to streamline the process of creating and managing daily delivery routes for a fleet of drivers. It takes a list of daily orders, processes them, and generates optimized routes based on geographical location, saving time and improving efficiency.

## 🌟 Features

-   **Automated Route Generation:** Upload an Excel or CSV file of daily orders to automatically generate optimized routes.
-   **Multi-Driver Support:** Splits orders among a specified number of drivers.
-   **Route Visualization:** Displays the generated routes and stops on an interactive map.
-   **Route Assignment:** Provides downloadable CSV files for each driver with their assigned stops.
-   **Historical Route Data:** View and reload previously generated routes.
-   **Samsara Integration:** Upload generated routes directly to the Samsara platform.

## 🏗️ Architecture

The application is built with a modern Python stack, separating the frontend, backend, and data processing tasks.

-   **Backend API:** A **FastAPI** application that exposes endpoints for route generation, status checking, and data retrieval.
-   **Frontend:** An interactive web interface built with **Streamlit**.
-   **Background Task Processing:** **Celery** with a **Redis** broker is used to handle long-running route generation tasks in the background without blocking the user interface.
-   **Database:** **Supabase** (a PostgreSQL-based service) is used for storing customer data, historical routes, and stops.
-   **Routing Engine:** **Google OR-Tools** is used to solve the Vehicle Routing Problem (VRP) and optimize the delivery sequences.

## 🚀 Getting Started

### Prerequisites

-   Python 3.9+
-   [Redis](https://redis.io/topics/quickstart) server running locally.
-   A Supabase account and project for database storage.

### 1. Clone the Repository

```bash
git clone <repository-url>
cd routes-splitter
```

### 2. Project Setup

```bash
cd routes-splitter
python -m venv .venv
source ./venev/bin/activate

pip install -r ../requirements.txt

# Create a .env file
# and add your Supabase credentials:
# ./.env
SUPABASE_URL="your_supabase_url"
SUPABASE_KEY="your_supabase_service_role_key"
SAMSARA_API_TOKEN="your_samsara_api_token"
```

### 3. Running the Application

You will need to run four separate processes in four different terminals.

**Terminal 1: Run the Redis Server**

```bash
# From the `backend/redis` directory
./run_redis.sh
```
This will start the Redis server, typically on `http://127.0.0.1:6379`.

**Terminal 2: Run the Celery Worker**

```bash
# From the `backend` directory
./run_celery.sh
```
This starts the Celery worker, which listens for and executes background tasks from the Redis queue.

**Terminal 3: Run the Backend API**

```bash
# From the `backend` directory
./run_api.sh
```
This will start the FastAPI server, typically on `http://127.0.0.1:8000`.

**Terminal 3: Run the Frontend Application**

```bash
# From the `frontend` directory
./run_frontend.sh
```
This will start the Streamlit server, and the application will be accessible in your browser, typically at `http://localhost:8501`.

## 📁 Project Structure

```
.
├── backend/
│   ├── src/wulfs_routing_api/  # FastAPI, Celery, and business logic
│   ├── run_api.sh              # Script to run the API
│   └── run_celery.sh           # Script to run the Celery worker
├── frontend/
│   ├── src/wulfs_routing_web/  # Streamlit application code
│   └── run_frontend.sh         # Script to run the frontend
├── data/                       # Sample data files
├── notebooks/                  # Jupyter notebooks for testing and analysis
├── requirements.txt            # Python dependencies for the project
└── README.md                   # This file
```
