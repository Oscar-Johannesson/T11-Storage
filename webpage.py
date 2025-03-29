from flask import Flask, redirect, url_for, session, request, render_template, flash, send_from_directory
import os
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os.path
from shared_state import load_state, save_state
import subprocess
import platform

app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = os.urandom(24)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

def load_users():
    try: 
        with open("dat/users.json", "r") as f:
            return json.load(f)
    except:
        default_users = {
            "admin": generate_password_hash("1234")
        }
        save_users(default_users)
        return default_users

def save_users(users):
    with open("dat/users.json", "w") as f:
        json.dump(users, f, indent=4)

users = load_users()

storage_items = {}

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "img", "icons")
PRESETS_FILE = os.path.join(os.path.dirname(__file__), "dat", "presets.json")

def load_presets():
    try:
        with open(PRESETS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def load_storage_data():
    json_filepath = os.path.join(os.path.dirname(__file__), "dat", "utilities.json")
    try:
        with open(json_filepath, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading storage data: {e}")
        return []

def get_active_searches():
    state = load_state()
    return state["searches"]

def sync_with_main():
    """Get current state from main.py"""
    try:
        import main
        return {
            "searches": main.searches,
            "rainbow": main.Rainbow
        }
    except ImportError:
        return {"searches": [], "rainbow": False}

@app.route("/")
def index():
    if not session.get("user"):
        return redirect(url_for("login"))
    storage_data = load_storage_data()
    active_searches = get_active_searches()
    return render_template("index.html", 
                         user=session["user"], 
                         items=storage_data,
                         active_searches=active_searches)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        # Reload users from file for each login attempt
        current_users = load_users()
        
        # Case-insensitive username match
        matching_user = next((u for u in current_users.keys() if u.lower() == username.lower()), None)
        
        if matching_user and check_password_hash(current_users[matching_user], password):
            session["user"] = {"name": matching_user}  # Use the original case from the stored username
            return redirect(url_for("index"))
        flash("Invalid username or password")
    return render_template("login.html")

# Change BASE_URL to use HTTP
BASE_URL = "http://localhost:5000"

@app.route("/microsoft_login")
def microsoft_login():
    flash("Microsoft har för höga krav på mig...")
    return redirect(url_for("login"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/add_item", methods=["POST"])
def add_item():
    if not session.get("user"):
        return redirect(url_for("login"))
    
    item_data = request.get_json()
    item_id = len(storage_items) + 1
    storage_items[item_id] = item_data
    return {"success": True, "item_id": item_id}

@app.route("/delete_item/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    if not session.get("user"):
        return redirect(url_for("login"))
    
    if item_id in storage_items:
        del storage_items[item_id]
        return {"success": True}
    return {"success": False, "error": "Item not found"}

@app.route("/api/storage_data")
def get_storage_data():
    if not session.get("user"):
        return {"error": "Unauthorized"}, 401
    return {"data": load_storage_data()}

@app.route("/api/active_searches")
def get_search_data():
    if not session.get("user"):
        return {"error": "Unauthorized"}, 401
    return {"searches": get_active_searches()}

@app.route("/api/state")
def get_state():
    if not session.get("user"):
        return {"error": "Not logged in", "redirect": url_for('login')}, 401
    return load_state()

@app.route("/toggle_item/<item_id>", methods=["POST"])
def toggle_item(item_id):
    if not session.get("user"):
        return {"success": False, "error": "Unauthorized"}, 401
    
    try:
        state = load_state()
        if item_id in state["searches"]:
            state["searches"].remove(item_id)
        else:
            state["searches"].append(item_id)
        save_state(state)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.route("/search_items")
def search_items():
    if not session.get("user"):
        return {"error": "Unauthorized"}, 401
    
    query = request.args.get("query", "").lower()
    results = []
    
    data = load_storage_data()
    for sublist in data:
        for item in sublist:
            if (query in item.get("utility", "").lower() or 
                query in item.get("keywords", "").lower()):
                results.append({
                    "Id": item["Id"],
                    "utility": item["utility"],
                    "description": item.get("description", "")
                })
    
    return {"results": results}

@app.route("/preset", methods=["GET", "POST"])
def add_preset():
    if not session.get("user"):
        return redirect(url_for("login"))
    return {"success": True}

@app.route("/save_preset", methods=["POST"])
def save_preset():
    if not session.get("user"):
        return {"success": False, "error": "Unauthorized"}, 401
    
    data = request.get_json()
    presets = load_presets()
    presets[data["name"]] = data["items"]
    
    with open(PRESETS_FILE, 'w') as f:
        json.dump(presets, f)
    
    return {"success": True}

@app.route("/add_component", methods=["POST"])
def add_component():
    if not session.get("user"):
        return {"success": False, "error": "Unauthorized"}, 401
    print("Adding component")
    print(request.form)
    try:
        name = request.form.get("componentName")
        category = request.form.get("componentCategory")
        description = request.form.get("componentDesc")
        
        
        if category == "resistor":
            icon = "resistor.png"
        elif category == "capacitor": 
            icon = "kondensator.png"
        elif category == "led":
            icon = "led.png"
        elif category == "diode":
            icon = "diode.png"
        elif category == "transistor":
            icon = "transistor.png"
        elif category == "motor":
            icon = "motor.png"
        elif category == "ic":
            icon = "ic.png"
        elif category == "sensor":
            icon = "sensor.png"
        elif category == "other":
            icon = "other.png"
        else:
            icon = "miscellaneous.png"

        data = load_storage_data()
        newid =  (int(data[-1][-1]["Id"] if data and data[-1] else 0)) + 1
        
        new_component = {
            "utility": name,
            "description": description,
            "icon": f"..img/icons/{icon}",
            "keywords": f"{name}",
            "favourite": "false",
            "number": "1",
            "Id": str(newid)
        }
        data.append([new_component])
        
        data = load_storage_data()
        if data:
            data[-1].append(new_component)
        else:
            data = [[new_component]]
            
        with open(os.path.join(os.path.dirname(__file__), "dat", "utilities.json"), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_component_details(component_id):
    data = load_storage_data()
    for sublist in data:
        for item in sublist:
            if item["Id"] == component_id:
                return item["utility"]
    return None

@app.route("/api/presets")
def get_presets():
    if not session.get("user"):
        return {"error": "Not logged in", "redirect": url_for('login')}, 401
    
    presets = load_presets()
    detailed_presets = {}
    
    for name, items in presets.items():
        components = []
        for item_id in items:
            component_name = get_component_details(item_id)
            if component_name:
                components.append(component_name)
        detailed_presets[name] = {
            "items": items,
            "components": components
        }
    
    return detailed_presets

@app.route("/api/load_preset", methods=["POST"])
def load_preset():
    if not session.get("user"):
        return {"error": "Not logged in"}, 401
    
    data = request.get_json()
    items = data.get("items", [])
    
    # Update the state with the preset items
    state = load_state()
    state["searches"] = items
    save_state(state)
    
    return {"success": True}

@app.route("/api/delete_preset", methods=["POST"])
def delete_preset():
    if not session.get("user"):
        return {"error": "Not logged in"}, 401
        
    data = request.get_json()
    name = data.get("name")
    
    presets = load_presets()
    if name in presets:
        del presets[name]
        with open(PRESETS_FILE, 'w') as f:
            json.dump(presets, f)
        return {"success": True}
    
    return {"error": "Preset not found"}, 404

@app.route("/api/clear_all", methods=["POST"])
def clear_all():
    if not session.get("user"):
        return {"error": "Not logged in"}, 401
    
    state = load_state()
    state["searches"] = []
    save_state(state)
    
    return {"success": True}

@app.route("/terminal")
def terminal():
    if not session.get("user"):
        return redirect(url_for("login"))
    system_info = f"{platform.system()} {platform.release()}"
    return render_template("terminal.html", user=session["user"], system_info=system_info)

@app.route("/terminal/execute", methods=["POST"])
def execute_command():
    if not session.get("user"):
        return {"error": "Not authorized"}, 401
    
    if platform.system() != 'Linux':
        return {"error": "Terminal commands only supported on Linux systems"}
    
    command = request.json.get("command")
    
    # List of allowed commands (for security)
    allowed_commands = ['ls', 'pwd', 'date', 'whoami', 'uname', 'df', 'free',
                       'top', 'ps', 'uptime', 'ip', 'hostname']
    
    # Basic command validation
    cmd_parts = command.split()
    base_cmd = cmd_parts[0] if cmd_parts else ''
    
    if base_cmd not in allowed_commands:
        return {"error": f"Command not allowed. Allowed commands: {', '.join(allowed_commands)}"}
    
    try:
        # Execute command with timeout
        result = subprocess.run(
            cmd_parts,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        output = result.stdout if result.returncode == 0 else result.stderr
        return {"output": output}
    
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
    except Exception as e:
        return {"error": str(e)}

@app.route("/api/users/add", methods=["POST"])
def add_user():
    if not session.get("user"):
        return {"error": "Unauthorized"}, 401
    
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            return {"error": "Missing username or password"}, 400
            
        users = load_users()
        if username in users:
            return {"error": "Username already exists"}, 400
            
        users[username] = generate_password_hash(password)
        save_users(users)
        users = load_users()  # Reload users after saving
        return {"success": True, "message": "User added successfully"}
    except Exception as e:
        return {"error": f"Failed to add user: {str(e)}"}, 500

@app.route("/api/users/list")
def list_users():
    if not session.get("user"):
        return {"error": "Unauthorized"}, 401
    
    users = load_users()
    return {"users": list(users.keys())}

@app.route("/api/users/change_password", methods=["POST"])
def change_password():
    if not session.get("user"):
        return {"error": "Unauthorized"}, 401
    
    data = request.get_json()
    current_password = data.get("currentPassword")
    new_password = data.get("newPassword")
    username = session["user"]["name"]
    
    users = load_users()
    if not check_password_hash(users[username], current_password):
        return {"error": "Current password is incorrect"}, 400
        
    users[username] = generate_password_hash(new_password)
    save_users(users)
    return {"success": True, "message": "Password changed successfully"}

@app.route("/api/users/delete/<username>", methods=["DELETE"])
def delete_user(username):
    if not session.get("user"):
        return {"error": "Unauthorized"}, 401
    
    if username == "admin":
        return {"error": "Cannot delete admin user"}, 400
        
    users = load_users()
    if username in users:
        del users[username]
        save_users(users)
        return {"success": True, "message": f"User {username} deleted successfully"}
    
    return {"error": "User not found"}, 404

@app.route("/api/toggle_search_lock", methods=["POST"])
def toggle_search_lock():
    if not session.get("user"):
        return {"error": "Not logged in"}, 401
    
    state = load_state()
    state["allow_searches"] = not state.get("allow_searches", True)
    
    # Clear searches when locking
    if not state["allow_searches"]:
        state["searches"] = []
        
    save_state(state)
    
    return {
        "success": True, 
        "allow_searches": state["allow_searches"],
        "searches": state["searches"]
    }

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True)