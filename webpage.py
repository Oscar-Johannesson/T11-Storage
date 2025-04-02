from flask import Flask, redirect, url_for, session, request, render_template, flash, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix; from werkzeug.security import generate_password_hash, check_password_hash; import json, os, os.path, subprocess, platform, shutil; from datetime import datetime; from shared_state import load_state, save_state

app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = os.urandom(24)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

def load_users():
    try: 
        with open("dat/users.json", "r") as f:
            data = json.load(f)
            updated = False
            for username, hash_value in data.items():
                if not hash_value.startswith('pbkdf2:sha256:'):
                    data[username] = generate_password_hash(hash_value.split('$')[-1])
                    updated = True
            if updated:
                save_users(data)
            return data
    except:
        default_users = {
            "admin": generate_password_hash("1234", method='pbkdf2:sha256')
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
    
def get_component_names():
    components = {}
    data = load_storage_data()
    for sublist in data:
        for item in sublist:
            components[item["Id"]] = {
                "name": item["utility"]
            }
    return components


@app.route("/")
def index():
    if not session.get("user"):
        return redirect(url_for("login"))
    storage_data = load_storage_data()
    active_searches = get_active_searches()
    components = get_component_names()
    return render_template("index.html", 
                        components=components,
                         user=session["user"], 
                         items=storage_data,
                         active_searches=active_searches)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        current_users = load_users()
        
        matching_user = next((u for u in current_users.keys() if u.lower() == username.lower()), None)
        
        if matching_user:
            stored_hash = current_users[matching_user]
            try:
                if check_password_hash(stored_hash, password):
                    session["user"] = {"name": matching_user}
                    return redirect(url_for("index"))
            except ValueError:
                # If old hash format causes error, regenerate hash
                current_users[matching_user] = generate_password_hash(password, method='pbkdf2:sha256')
                save_users(current_users)
                session["user"] = {"name": matching_user}
                return redirect(url_for("index"))
                
        flash("Invalid username or password")
    return render_template("login.html")

BASE_URL = "http://localhost:5000"

@app.route("/microsoft_login")
def microsoft_login():
    flash("Microsoft har för höga krav...")
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
    
    try:
        component_id = request.form.get("componentId")
        name = request.form.get("componentName")
        category = request.form.get("componentCategory")
        description = request.form.get("componentDesc")
        
        # Icon selection logic
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

        new_component = {
            "utility": name,
            "description": description,
            "icon": f"..img/icons/{icon}",
            "keywords": f"{name}",
            "favourite": "false",
            "number": "1",
            "Id": str(component_id)
        }

        data = load_storage_data()
        
        # Look for existing component with same ID to replace
        found = False
        for sublist in data:
            for i, item in enumerate(sublist):
                if item["Id"] == str(component_id):
                    sublist[i] = new_component
                    found = True
                    break
            if found:
                break
                
        # If no existing component found, add to last sublist
        if not found:
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
    
    allowed_commands = ['ls', 'cd', 'date', 'whoami', 'reboot', 'uptime', 'ip', 'hostname', 'shutdown', 'nano', 'reinstall']
    
    cmd_parts = command.split()
    base_cmd = cmd_parts[0] if cmd_parts else ''
    
    if base_cmd not in allowed_commands:
        return {"error": f"Command not allowed. Allowed commands: {', '.join(allowed_commands)}"}
    
    if base_cmd == 'reinstall': #denna är en custom commafo för att instalera och validera att filerna är rätt variant
        try:
            repo_path = os.path.join(os.path.dirname(__file__), "temp_repo")
            if os.path.exists(repo_path):
                shutil.rmtree(repo_path)
            
            subprocess.run(["git", "clone", "https://github.com/Oscar-Johannesson/T11-Storage.git", repo_path], check=True)
            
            required_files = ["dat/utilities.json", "dat/presets.json"]
            template_files = ["templates/index.html", "templates/login.html", "templates/terminal.html"]
            python_files = ["main.py", "shared_state.py", "webpage.py"]

            for file in required_files:
                src = os.path.join(repo_path, file)
                dst = os.path.join(os.path.dirname(__file__), file)
                if os.path.exists(src):
                    with open(src, 'r') as f:
                        json.load(f)  
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                else:
                    raise FileNotFoundError(f"Required file {file} not found in repository")

            for file in template_files:
                src = os.path.join(repo_path, file)
                dst = os.path.join(os.path.dirname(__file__), file)
                if os.path.exists(src):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                else:
                    raise FileNotFoundError(f"Required template {file} not found in repository")

            for file in python_files:
                src = os.path.join(repo_path, file)
                dst = os.path.join(os.path.dirname(__file__), file)
                if os.path.exists(src):
                    with open(src, 'r') as f:
                        compile(f.read(), file, 'exec') 
                    shutil.copy2(src, dst)
                else:
                    raise FileNotFoundError(f"Required Python file {file} not found in repository")

            shutil.rmtree(repo_path)
            
        except Exception as e:
            return {"error": f"Failed to reinstall files: {str(e)}"}
        
        return {"success": True, "message": "validated files reinstalled"}

    
    try:
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
            
        users[username] = generate_password_hash(password, method='pbkdf2:sha256')
        save_users(users)
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
    try:
        if check_password_hash(users[username], current_password):
            users[username] = generate_password_hash(new_password, method='pbkdf2:sha256')
            save_users(users)
            return {"success": True, "message": "Password changed successfully"}
    except ValueError:
        pass
    return {"error": "Current password is incorrect"}, 400

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
    
        
    save_state(state)
    
    return {
        "success": True, 
        "allow_searches": state["allow_searches"],
        "searches": state["searches"]
    }

@app.route("/download/<filename>")
def download_backup(filename):
    if not session.get("user"):
        return {"error": "Not logged in"}, 401
        
    allowed_files = ['users.json', 'presets.json', 'utilities.json']
    if filename not in allowed_files:
        return {"error": "File not allowed"}, 403
        
    try:
        date_str = datetime.now().strftime('%Y-%m-%d')
        source_path = os.path.join('dat', filename)
        
        backup_filename = f"{date_str}_backup_{filename}"
        
        temp_path = os.path.join('dat', backup_filename)
        shutil.copy2(source_path, temp_path)
        
        response = send_from_directory('dat', backup_filename, as_attachment=True)
        
        @response.call_on_close
        def cleanup():
            try:
                os.remove(temp_path)
            except:
                pass
                
        return response
        
    except Exception as e:
        return {"error": f"Failed to create backup: {str(e)}"}, 500

@app.route("/api/upload_backup", methods=["POST"])
def upload_backup():
    if not session.get("user"):
        return {"error": "Not logged in"}, 401
        
    if 'file' not in request.files:
        return {"error": "No file provided"}, 400
        
    file = request.files['file']
    backup_type = request.form.get('type')
    
    if not backup_type or backup_type not in ['users.json', 'presets.json', 'utilities.json']:
        return {"error": "Invalid backup type"}, 400
        
    if file.filename == '':
        return {"error": "No file selected"}, 400
        
    if not file.filename.endswith('.json'):
        return {"error": "File must be JSON format"}, 400
        
    try:
        try:
            json.load(file)
            file.seek(0)  
        except:
            return {"error": "Invalid JSON file"}, 400
            
        target_path = os.path.join('dat', backup_type)
        
        if os.path.exists(target_path):
            backup_name = os.path.join('dat', f'Old_{backup_type}')
            if os.path.exists(backup_name):
                os.remove(backup_name)  
            os.rename(target_path, backup_name)
            
        file.save(target_path)
        
        return {"success": True, "message": "Backup uploaded successfully"}
        
    except Exception as e:
        return {"error": f"Failed to upload backup: {str(e)}"}, 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True)