"""
Setup Sample SQLite Database for MCP Server Demo
Creates a sample database with tables and data for testing
"""
import sqlite3
import json
from datetime import datetime, timedelta
import random

def create_sample_database():
    """Create a sample SQLite database with realistic data"""
    
    # Connect to database (creates it if it doesn't exist)
    conn = sqlite3.connect('example.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            age INTEGER,
            department TEXT,
            hire_date DATE,
            salary REAL,
            active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Create projects table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            start_date DATE,
            end_date DATE,
            budget REAL,
            status TEXT DEFAULT 'planning'
        )
    ''')
    
    # Create tasks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            user_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'todo',
            due_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create orders table (for e-commerce example)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            total_amount REAL,
            status TEXT DEFAULT 'pending',
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Sample data for users
    users_data = [
        ('Alice Johnson', 'alice@company.com', 28, 'Engineering', '2022-01-15', 75000, True),
        ('Bob Smith', 'bob@company.com', 34, 'Marketing', '2021-03-10', 65000, True),
        ('Charlie Brown', 'charlie@company.com', 29, 'Engineering', '2022-06-01', 80000, True),
        ('Diana Prince', 'diana@company.com', 32, 'Design', '2020-11-20', 70000, True),
        ('Eve Wilson', 'eve@company.com', 26, 'Sales', '2023-02-14', 60000, True),
        ('Frank Miller', 'frank@company.com', 38, 'Engineering', '2019-08-05', 90000, False),
        ('Grace Lee', 'grace@company.com', 30, 'HR', '2021-12-01', 55000, True),
        ('Henry Davis', 'henry@company.com', 35, 'Marketing', '2020-05-15', 68000, True)
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO users (name, email, age, department, hire_date, salary, active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', users_data)
    
    # Sample projects
    projects_data = [
        ('Website Redesign', 'Complete overhaul of company website with modern UI/UX', '2024-01-01', '2024-06-30', 50000, 'active'),
        ('Mobile App Development', 'Develop iOS and Android mobile application', '2024-02-15', '2024-12-31', 120000, 'active'),
        ('Database Migration', 'Migrate legacy database to cloud infrastructure', '2023-11-01', '2024-03-31', 75000, 'completed'),
        ('Marketing Campaign Q2', 'Social media and digital marketing campaign for Q2', '2024-04-01', '2024-06-30', 30000, 'planning'),
        ('AI Integration', 'Integrate AI tools into existing workflows', '2024-03-01', '2024-09-30', 200000, 'active')
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO projects (name, description, start_date, end_date, budget, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', projects_data)
    
    # Sample tasks
    tasks_data = [
        (1, 1, 'Design mockups', 'Create initial design mockups for homepage', 'high', 'completed', '2024-01-15'),
        (1, 4, 'User research', 'Conduct user interviews and surveys', 'medium', 'completed', '2024-01-20'),
        (1, 3, 'Frontend development', 'Implement responsive frontend components', 'high', 'in_progress', '2024-02-28'),
        (2, 3, 'Setup development environment', 'Configure React Native development setup', 'medium', 'completed', '2024-02-20'),
        (2, 1, 'API integration', 'Integrate backend APIs with mobile app', 'high', 'todo', '2024-04-15'),
        (3, 1, 'Data backup', 'Create comprehensive backup of legacy data', 'critical', 'completed', '2023-12-01'),
        (3, 3, 'Migration scripts', 'Develop automated migration scripts', 'high', 'completed', '2024-01-30'),
        (4, 2, 'Social media strategy', 'Develop comprehensive social media strategy', 'medium', 'in_progress', '2024-04-30'),
        (5, 1, 'Research AI tools', 'Evaluate different AI tools and platforms', 'medium', 'completed', '2024-03-15'),
        (5, 3, 'Proof of concept', 'Build AI integration proof of concept', 'high', 'in_progress', '2024-05-30')
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO tasks (project_id, user_id, title, description, priority, status, due_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', tasks_data)
    
    # Sample orders
    orders_data = []
    for i in range(20):
        user_id = random.randint(1, 8)
        amount = round(random.uniform(25.99, 299.99), 2)
        status = random.choice(['pending', 'completed', 'shipped', 'cancelled'])
        days_ago = random.randint(1, 90)
        order_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M:%S')
        orders_data.append((user_id, amount, status, order_date))
    
    cursor.executemany('''
        INSERT OR IGNORE INTO orders (user_id, total_amount, status, order_date)
        VALUES (?, ?, ?, ?)
    ''', orders_data)
    
    # Commit changes and close
    conn.commit()
    
    # Print summary
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM projects")  
    project_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tasks")
    task_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM orders")
    order_count = cursor.fetchone()[0]
    
    print("✅ Sample database created successfully!")
    print(f"📊 Database contents:")
    print(f"   • Users: {user_count}")
    print(f"   • Projects: {project_count}")
    print(f"   • Tasks: {task_count}")
    print(f"   • Orders: {order_count}")
    
    conn.close()

def show_sample_queries():
    """Display some sample SQL queries that work with the database"""
    print("\n💡 Sample SQL queries you can try:")
    
    queries = [
        "SELECT * FROM users WHERE department = 'Engineering'",
        "SELECT p.name, COUNT(t.id) as task_count FROM projects p LEFT JOIN tasks t ON p.id = t.project_id GROUP BY p.id",
        "SELECT u.name, SUM(o.total_amount) as total_spent FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.id ORDER BY total_spent DESC",
        "SELECT * FROM tasks WHERE status = 'in_progress' AND priority = 'high'",
        "SELECT department, AVG(salary) as avg_salary FROM users WHERE active = 1 GROUP BY department",
        "SELECT p.name as project, t.title, u.name as assigned_to FROM projects p JOIN tasks t ON p.id = t.project_id JOIN users u ON t.user_id = u.id WHERE t.status != 'completed'"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"   {i}. {query}")

if __name__ == "__main__":
    create_sample_database()
    show_sample_queries()