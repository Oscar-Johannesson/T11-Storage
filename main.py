import os, json, random
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageFilter
import threading
from tkinter import messagebox
import subprocess
from shared_state import load_state, save_state, start_file_monitor
import time
from multiprocessing import Process




searches = []
Rainbow = False 
allow_searches = True
should_animate = False
a_light_sleep = True

    

def toggle_lights():
    global Rainbow
    try:
        try:
            import board
            import neopixel
        except ImportError:
            print("Warning: RPi libraries not available")
            return

        pixel_pin = board.D18
        num_pixels = 360
        ORDER = neopixel.GRB
        
        pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=1.0, auto_write=False, pixel_order=ORDER)
        

        pixels.fill((0, 0, 0))
   
            
        pixels.fill((0, 0, 0)) 
        for search_id in searches:
            search_id = int(search_id)
            if 1 <= search_id <= num_pixels: 
                if Rainbow and search_id == len(searches): 
                    def rainbow_cycle():
                            for i in range(255):
                                r = int((1 + i) % 255)
                                g = int((85 + i) % 255) 
                                b = int((170 + i) % 255)
                                pixels[int(search_id-1)] = (r, g, b)
                                time.sleep(0.01)
                                pixels.show()
                            pixels[int(search_id)-1] = (255, 255, 255)
                    rainbow_process = Process(target=rainbow_cycle)
                    rainbow_process.daemon = True
                    rainbow_process.start()
                else:
                    pixels[int(search_id)-1] = (255, 255, 255)  
                    
        pixels.show()
    except ImportError as e:
        print(e)
        messagebox.showerror("Import Error", "Could not import required modules: " + str(e))
    except Exception as e:
        print(e)
        messagebox.showerror("Light Control Error", "Error controlling lights: " + str(e))

def periodic_update():
    global should_animate, searches
    try:
        old_searches = searches
        update_searches()
        if old_searches != searches:
            should_animate = False
        
        if not should_animate:
            if os.name != 'nt':
                toggle_lights()
        root.after(5000, periodic_update)
    except:
        pass

def update_searches():
    global searches, root
    json_filepath = os.path.join(os.path.dirname(__file__), "dat", "utilities.json")
    with open(json_filepath, "r", encoding="utf-8") as file:
        data = json.load(file)
        
    try:
        root.search_history_frame.destroy()
    except:
        pass

    root.search_history_frame = tk.Frame(root, bg='#a0a0a0')
    root.search_history_frame.place(x=root.winfo_width() - 200, y=180)
   
    for search_id in searches:
        for sublist in data:
            for item in sublist:
                if item["Id"] == search_id:
                    search_box = tk.Frame(root.search_history_frame, bg='#505050', bd=2, relief="groove")
                    search_box.pack_propagate(False)
                    search_box.config(width=180, height=50)
                    search_box.pack(anchor='w', pady=2)

                    if os.name == 'nt':  
                        icon_path = os.path.join(os.path.dirname(__file__), item["icon"].replace("..", "").replace("/", "\\"))
                    else:  
                        icon_path = os.path.join(os.path.dirname(__file__), item["icon"].replace("..", ""))

                    try:
                        icon_image = ImageTk.PhotoImage(Image.open(icon_path).resize((30, 30), Image.Resampling.LANCZOS))
                    except FileNotFoundError:
                        icon_image = None

                    if icon_image:
                        icon_label = tk.Label(search_box, image=icon_image, bg='#505050')
                        icon_label.image = icon_image
                        icon_label.pack(side=tk.LEFT, padx=5, pady=5)

                    text_label = tk.Label(search_box, text=item['utility'], font=("Arial", 10), bg='#505050', fg='white', wraplength=140, justify="left")
                    text_label.pack(side=tk.LEFT, padx=5, pady=5)
    

def search_data(searchphrase):
    global root, allow_searches
    if not allow_searches:
        messagebox.showerror("Error - blocked by admin", "Searches are disabled by admin")
        return
    
    json_filepath = os.path.join(os.path.dirname(__file__), "dat", "utilities.json")
    presets_filepath = os.path.join(os.path.dirname(__file__), "dat", "presets.json")
    
    with open(json_filepath, "r", encoding="utf-8") as file:
        data = json.load(file)
    
    try:
        with open(presets_filepath, "r", encoding="utf-8") as file:
            presets_data = json.load(file)
    except:
        presets_data = {}
    
    results = []
    for sublist in data:
        for item in sublist:
            if searchphrase.lower() in item.get("utility", "").lower() or searchphrase.lower() in item.get("keywords", "").lower():
                results.append(item["Id"])

    for preset_name, preset_ids in presets_data.items():
        if searchphrase.lower() in preset_name.lower():
            preset_item = {
                "Id": f"preset:{preset_name}",  # Add prefix to avoid ID conflicts
                "utility": f"Preset: {preset_name}",
                "description": f"Contains {len(preset_ids)} items",
                "icon": os.path.join(os.path.dirname(__file__), "img", "icons", "preset.png"),
                "preset_ids": preset_ids
            }
            results.append(preset_item)

    if hasattr(root, 'result_frame') or searchphrase == "": 
        root.result_frame.destroy()

    if results and searchphrase != "":
        root.result_frame = tk.Frame(root, bg='#a0a0a0')
        root.result_frame.place(relx=0.5, rely=0.2, anchor="n")
        def on_mouse_wheel(event):
            result_list.yview_scroll(int(-1*(event.delta/120)), "units")

        root.bind_all("<MouseWheel>", on_mouse_wheel)
        scrollbar = tk.Scrollbar(root.result_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        root.update_idletasks()
        widthh = 60 if root.winfo_width() <= 800 else 60
        result_list = tk.Text(root.result_frame, yscrollcommand=scrollbar.set, width=widthh, height=25, font=("Arial", 14), bg='#a0a0a0', fg='white')
        result_list.pack(side=tk.LEFT, fill=tk.BOTH)

        scrollbar.config(command=result_list.yview)
        image_cache = {}

        for result in results:
            if isinstance(result, dict):  
                item = result
            else:  
                item = next((item for sublist in data for item in sublist if item["Id"] == result), None)
            
            if item:
                if os.name == 'nt': 
                    icon_path = os.path.join(os.path.dirname(__file__), item["icon"].replace("..", "").replace("/", "\\"))
                else: 
                    icon_path = os.path.join(os.path.dirname(__file__), item["icon"].replace("..", ""))

                if icon_path in image_cache:
                    icon_image = image_cache[icon_path]
                else:
                    try:
                        icon_image = ImageTk.PhotoImage(Image.open(icon_path).resize((70, 70), Image.Resampling.LANCZOS))
                        image_cache[icon_path] = icon_image
                    except FileNotFoundError:
                        icon_image = None

                root.update_idletasks()
                result_box = tk.Frame(result_list, bg='#505050', bd=2, relief="groove")
                
                if isinstance(item.get("Id"), str) and item["Id"].startswith("preset:"):
                    if all(str(pid) in searches for pid in item["preset_ids"]):
                        result_box.config(bg='#19cb07')
                elif item["Id"] in searches:
                    result_box.config(bg='#19cb07')
                    
                result_box.pack_propagate(False)
                boxy_widty = root.result_frame.winfo_width()
                result_box.config(width=boxy_widty, height=100)
                result_list.window_create(tk.END, window=result_box)
                result_list.insert(tk.END, "\n")
                result_list.tag_configure("center", justify='center')
                result_list.tag_add("center", "1.0", "end")

                def on_click(event, item=item, box=result_box):
                    global searches
                    current_color = box.cget("bg")
                    new_color = '#19cb07' if current_color == '#505050' else '#505050'
                    box.config(bg=new_color)
                    
                    if isinstance(item.get("Id"), str) and item["Id"].startswith("preset:"):
                        preset_ids = item["preset_ids"]
                        if new_color == '#19cb07':
                            for pid in preset_ids:
                                if str(pid) not in searches:
                                    searches.append(str(pid))
                        else:
                            searches = [s for s in searches if s not in preset_ids]
                    else:
                        if new_color == '#19cb07':
                            searches.append(item["Id"])
                        else:
                            searches.remove(item["Id"])
                            
                    save_state({"searches": searches, "rainbow": Rainbow})
                    update_searches()
                    if os.name != 'nt':
                        toggle_lights()

                result_box.bind("<Button-1>", on_click)
                result_box.tag = item["Id"]

                if icon_image:
                    icon_label = tk.Label(result_box, image=icon_image, bg='#505050')
                    icon_label.image = icon_image
                    icon_label.pack(side=tk.LEFT, padx=5, pady=5)
                    icon_label.bind("<Button-1>", lambda e, i=item: on_click(e, i, result_box))

                text_label = tk.Label(result_box, text=f"{item['utility']}: {item['description']}", 
                                    font=("Arial", 14), bg='#505050', fg='white', 
                                    wraplength=700, justify="left")
                text_label.pack(side=tk.LEFT, padx=5, pady=5)
                text_label.bind("<Button-1>", lambda e, i=item: on_click(e, i, result_box))

                     
def sleep_animation(canvas, increment_timer):
    global backround, root, should_animate, a_light_sleep
    should_animate = True
    def rainbow_backround():
        global backround, should_animate, a_light_sleep
        try:
            if not should_animate:
                return
            if not hasattr(backround, 'is_animating'):
                return
            
            import board
            import neopixel
            pixel_pin = board.D18
            num_pixels = 360
            ORDER = neopixel.GRB

            pixels = neopixel.NeoPixel(
                pixel_pin, num_pixels, brightness=0.2, auto_write=False, pixel_order=ORDER
            )


            def wheel(pos):
                if pos < 0 or pos > 255:
                    r = g = b = 0
                elif pos < 85:
                    r = int(pos * 3)
                    g = int(255 - pos * 3)
                    b = 0
                elif pos < 170:
                    pos -= 85
                    r = int(255 - pos * 3)
                    g = 0
                    b = int(pos * 3)
                else:
                    pos -= 170
                    r = 0
                    g = int(pos * 3)
                    b = int(255 - pos * 3)
                return (r, g, b) if ORDER in (neopixel.RGB, neopixel.GRB) else (r, g, b, 0)


            def rainbow_cycle(wait):
                for j in range(0, 255):
                    for i in range(int(num_pixels/3)):
                        if not hasattr(backround, 'is_animating') or not should_animate:
                            pixels.fill((0, 0, 0)) 
                            pixels.show()
                            return
                        pixel_index = (i * 256 // num_pixels) + j
                        pixels[i] = wheel(pixel_index & 255)
                        pixels[i+120] = wheel(pixel_index & 255)
                        pixels[i+240] = wheel(pixel_index & 255)
                    pixels.show()
                    time.sleep(0.001)
            def rainbow_text(text):
                letters = {
                    'G': [
                        [1,1,1,1,1],
                        [1,0,0,0,0],
                        [1,0,1,1,1],
                        [1,0,0,0,1],
                        [1,1,1,1,1]
                    ],
                    'T': [
                        [1,1,1,1,1],
                        [0,0,1,0,0],
                        [0,0,1,0,0],
                        [0,0,1,0,0],
                        [0,0,1,0,0]
                    ]
                }

                text_pixels = []
                for char in text:
                    if char in letters:
                        for row in letters[char]:
                            text_pixels.append(row)
                        text_pixels.append([0,0,0,0,0])

                pattern_width = len(text_pixels[0])
                pattern_height = len(text_pixels)
                
                pixels.fill((0, 0, 0))
                pixels.show()
                
                for col in range(0, 3):  
                    for y in range(pattern_height):
                        for x in range(pattern_width):
                            if not hasattr(backround, 'is_animating') or not should_animate:
                                return
                                
                            base_pos = col * 120
                            led_pos = base_pos + (y * 5 + x)
                            
                            if y < len(text_pixels) and x < len(text_pixels[y]):
                                if text_pixels[y][x] == 1:
                                    hue = (x * 50 + y * 10) % 255
                                    r,g,b = wheel(hue)
                                    if led_pos < num_pixels:
                                        pixels[led_pos] = (r,g,b)
                                else:
                                    if led_pos < num_pixels:
                                        pixels[led_pos] = (0, 0, 0)  
                pixels.show()
                time.sleep(0.1)

                

            while True:
                if not hasattr(backround, 'is_animating') or not should_animate and a_light_sleep:
                    pixels.fill((0, 0, 0)) 
                    pixels.show()
                    return
                rainbow_text('GTG')
                time.sleep(0.1)
                rainbow_cycle(0.00001)
        except ImportError as e:
            print("Warning: RPi libraries not available")
        except Exception as e:
            messagebox.showerror("Error", "Error in rainbow_backround: " + str(e))

    try:
        if should_animate:
            backround = tk.Frame(canvas, width=canvas.winfo_width(), height=canvas.winfo_height(), bg='black')
            backround.pack_propagate(False)
            backround.place(x=0, y=0)
            image_path = os.path.join(os.path.dirname(__file__), "img", "GTG_spets.png")
            screen_width = canvas.winfo_width()
            screen_height = canvas.winfo_height()
            image_size = min(screen_width, screen_height) // 8

            image = Image.open(image_path).convert('RGBA')
            resized_image = image.resize((image_size, image_size), Image.Resampling.LANCZOS)

            mask = Image.new('L', (image_size, image_size), 0)
            draw = ImageDraw.Draw(mask)
            padding = 1
            draw.ellipse((padding, padding, image_size-padding, image_size-padding), fill=255)
            mask = mask.filter(ImageFilter.BLUR)

            resized_image.putalpha(mask)

            photo_image = ImageTk.PhotoImage(resized_image)
            image_label = tk.Label(backround, image=photo_image, bg='black')
            image_label.image = photo_image
            
            x, y = 0, 0
            dx, dy = 2, 2
            
            def move_image():
                global backround
                nonlocal x, y, dx, dy
                
                x += dx
                y += dy
                
                if x <= 0 or x + image_label.winfo_width() >= backround.winfo_width():
                    dx *= -1
                if y <= 0 or y + image_label.winfo_height() >= backround.winfo_height():
                    dy *= -1
                    
                image_label.place(x=x, y=y)
                
                if should_animate:
                    backround.after(20, move_image)
            
            move_image()
            backround.is_animating = True
            should_animate = True
            if a_light_sleep:
                backround.rainbowthread = threading.Thread(target=rainbow_backround, daemon=True).start()

            def stop_animation(event=None):
                global backround, should_animate
                backround.is_animating = False
                should_animate = False

                backround.destroy()
                root.unbind_all('<Key>')
                root.unbind_all('<Button-1>')
                root.unbind_all('<Button-2>')
                root.unbind_all('<Button-3>')
                root.unbind_all('<Motion>')
                root.update_idletasks()
                root.after(1000, increment_timer) 
            time.sleep(0.5)
            root.bind_all('<Key>', stop_animation)
            root.bind_all('<Button-1>', stop_animation)
            root.bind_all('<Button-2>', stop_animation)
            root.bind_all('<Button-3>', stop_animation)
            root.bind_all('<Motion>', stop_animation)
            
    except Exception as e:
        print("error in sleep animation:", str(e))

def start_idle_timer():
    global idle_timer
    idle_timer = 0

    def increment_timer():
        global idle_timer
        idle_timer += 1 # ändra så denna rad ska vara en kommen tar eller inte om man vill att sytemet automatisk går in i "sleep mode"
        if idle_timer >= 600:  # ändra denna till hur länge den ska vara idle innan den går in i "sleep mode" ( 600 = 10 min )
            sleep_animation(root, start_idle_timer)  
        else:
            root.after(1000, increment_timer) 

    increment_timer()

def reset_idle_timer(event=None):
    global idle_timer
    idle_timer = 0




def main_ui():
    global root, A_Animate
    root = tk.Tk()
    A_Animate = False
    root.title("Använd piltangenterna för att styra din figur")
    root.geometry("800x500")
    root.attributes('-fullscreen', True)
    if os.name == 'nt':
        def toggle_fullscreen(event=None):
            state = not root.attributes('-fullscreen')
            root.attributes('-fullscreen', state)
            if not state:
                root.state('zoomed')
        root.bind('<F11>', toggle_fullscreen)

    def update_from_state(state):
        global searches, Rainbow, allow_searches, a_light_sleep
        searches = state["searches"]
        Rainbow = state["rainbow"]
        a_light_sleep = state["a_light_sleep"]
        allow_searches = state.get("allow_searches", True)
        if hasattr(root, 'search_history_frame'):
            root.after(0, update_searches)
            root.after(0, toggle_lights)

    start_file_monitor(update_from_state)

    root.bind_all("<Motion>", reset_idle_timer)  
    root.bind_all("<Key>", reset_idle_timer)    
    root.bind_all("<Button>", reset_idle_timer) 

    start_idle_timer()

    def settings():
        if hasattr(root, 'settings_canvas') and root.settings_canvas.winfo_exists(): 
            root.settings_canvas.destroy()
        else:  
            canvas_width = root.winfo_width()/1.5
            canvas_height = root.winfo_height()/1.5
            root.settings_canvas = tk.Canvas(root, width=canvas_width, height=canvas_height)
            root.settings_canvas.place(relx=0.5, rely=0.5, anchor="center")
            
            root.settings_canvas.create_rectangle(0, 0, canvas_width, 100, fill="#808080")
            settings_label = tk.Label(root.settings_canvas, text="Settings", font=("Arial", 20), bg='#808080', fg='white')
            settings_label.place(relx=0.5, rely=0.05, anchor="center")
            
            section_width = canvas_width/3
            
            root.settings_canvas.create_rectangle(0, 100, section_width, canvas_height, fill="#a0a0a0")
            backround_options_label = tk.Label(root.settings_canvas, text="Background Options", font=("Arial", 16), bg='#a0a0a0', fg='black', width=15)
            backround_options_label.place(x=section_width/2, rely=0.2, anchor="center")
            
            root.settings_canvas.create_rectangle(section_width, 100, section_width*2, canvas_height, fill="#a0a0a0")
            network_options_label = tk.Label(root.settings_canvas, text="Network Options", font=("Arial", 16), bg='#a0a0a0', fg='black', width=15)
            network_options_label.place(x=section_width*1.5, rely=0.2, anchor="center")
            
            root.settings_canvas.create_rectangle(section_width*2, 100, section_width*3, canvas_height, fill="#a0a0a0")
            third_options_label = tk.Label(root.settings_canvas, text="Other Options", font=("Arial", 16), bg='#a0a0a0', fg='black', width=15)
            third_options_label.place(x=section_width*2.5, rely=0.2, anchor="center")
            
            close_button = tk.Button(root.settings_canvas, text="X", command=settings, font=("Arial", 12), bg='#808080', fg='red')
            close_button.place(relx=0.999, rely=0.03, anchor='e')

            def create_toggle(locationX, locationY, callFunction, sidetext, canvas_to_place_on, use_pack=False):
                frame = tk.Frame(canvas_to_place_on, width=60, height=30, bg='#a0a0a0')
                frame.pack_propagate(False)
                
                switch = tk.Canvas(frame, width=60, height=30, highlightthickness=0, bg='#a0a0a0')
                switch.pack()

                def draw_toggle(on=False):
                    switch.delete("all")
                    bg_color = '#19cb07' if on else '#505050'
                    switch.create_rounded_rectangle(0, 0, 60, 25, 15, fill=bg_color)
                    switch.create_oval(38 if on else 6, 4, 54 if on else 22, 20, fill='white')

                switch.create_rounded_rectangle = lambda x1, y1, x2, y2, r, **kwargs: switch.create_polygon(
                    [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r, x2,y2, x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1],
                    smooth=True, **kwargs)

                def toggle(e):
                    switch.on = not getattr(switch, 'on', False)
                    draw_toggle(switch.on)
                    callFunction(switch.on)

                frame.bind('<Button-1>', toggle)
                switch.bind('<Button-1>', toggle)
            
                func_name = callFunction.__name__
                
                state_vars = {
                    'allow_animate_background': 'A_Animate',
                    'myra': 'myra', 
                    'rainbow_toggle': 'Rainbow',
                    'rainbow_backround_allow_lights': 'a_light_sleep'
                }
                
                if func_name in state_vars and state_vars[func_name] in globals():
                    draw_toggle(callFunction(checkstatus=True))
                else:
                    draw_toggle()
                
                if use_pack:
                    frame.pack()
                else:
                    frame.place(x=locationX, y=locationY)
                
                label = tk.Label(canvas_to_place_on, text=sidetext, 
                                 font=("Arial", 12), bg='#a0a0a0', fg='white')
                if use_pack:
                    label.pack(padx=(70, 0), pady=5)
                else:
                    label.place(x=locationX + 70, y=locationY + 5)
                
                return frame
               

            def allow_animate_background(is_on=False, checkstatus=False):
                global A_Animate 
                if checkstatus:
                    return A_Animate
                A_Animate = is_on


            create_toggle(30, 200, allow_animate_background, "Allow animated backgrounds", root.settings_canvas)

            def update_background_list():
                background_frame = tk.Frame(root.settings_canvas, bg='#a0a0a0')
                background_frame.place(x=30, y=250)
                preview_frame = tk.Frame(background_frame, bg='#505050')
                preview_frame.pack(pady=10)

                preview_width = int(section_width * 0.6)  
                preview_height = int(preview_width * 0.5) 

                left_button = tk.Button(preview_frame, text="<", command=lambda: change_preview(-1))
                left_button.pack(side=tk.LEFT, padx=5)

                preview_label = tk.Label(preview_frame, bg='#505050')
                preview_label.pack(side=tk.LEFT, padx=5)

                right_button = tk.Button(preview_frame, text=">", command=lambda: change_preview(1))
                right_button.pack(side=tk.LEFT, padx=5)

                bg_path = os.path.join(os.path.dirname(__file__), "img", "background")
                bg_files = [f for f in os.listdir(bg_path) if f.endswith(('.png', '.gif'))]

                current_bg = "main-background.png"  # start bild ändra här för att ändra start bakgrund
                try:
                    for widget in root.winfo_children():
                        if isinstance(widget, tk.Canvas) and widget != root.settings_canvas:
                            current_bg = os.path.basename(widget.image.name_)
                            break
                except:
                    pass

                current_preview = {"index": bg_files.index(current_bg) if current_bg in bg_files else 0}

                def change_preview(direction):
                    current_preview["index"] = (current_preview["index"] + direction) % len(bg_files)
                    show_preview(bg_files[current_preview["index"]])
                    update_background(bg_files[current_preview["index"]])

                def animate_gif(canvas, img, frame_index=0):
                    try:
                        if not A_Animate or not hasattr(canvas, 'is_animating'):
                            return
                        canvas.delete('gif')
                        canvas.create_image(0, 0, image=img[frame_index], anchor="nw", tags='gif')
                        next_frame = (frame_index + 1) % len(img)
                        canvas.after(60 - (50 if current_bg == "one_and_zeroes.gif"else 0), lambda: animate_gif(canvas, img, next_frame))
                    except:
                        pass

                def show_preview(filename):
                    bg_path = os.path.join(os.path.dirname(__file__), "img", "background", filename)
                    image = Image.open(bg_path)
                    preview = image.resize((preview_width, preview_height), Image.Resampling.LANCZOS)
                    
                    for widget in preview_label.winfo_children():
                        if isinstance(widget, tk.Button):
                            widget.destroy()
                    
                    if filename.endswith('.gif'):
                        if A_Animate:
                            frames = []
                            try:
                                while True:
                                    preview = image.resize((preview_width, preview_height), Image.Resampling.LANCZOS)
                                    frames.append(ImageTk.PhotoImage(preview))
                                    image.seek(len(frames))
                            except EOFError:
                                pass
                            preview_label.frames = frames
                            animate_gif(preview_label, frames)
                            photo = ImageTk.PhotoImage(preview)
                            preview_label.configure(image=photo)
                            preview_label.image = photo
                            select_btn = tk.Button(preview_label, text="Select", 
                                                 command=lambda f=filename: update_background(f))
                            select_btn.place(relx=1.0, rely=0, anchor='ne')
                        else:
                            photo = ImageTk.PhotoImage(preview)
                            preview_label.configure(image=photo)
                            preview_label.image = photo
                            lock_label = tk.Label(preview_label, text="LOCKED", 
                                                bg='black', fg='red',
                                                font=('Arial', 16, 'bold'))
                            lock_label.place(relx=0.5, rely=0.5, anchor='center')
                    else:
                        photo = ImageTk.PhotoImage(preview)
                        preview_label.configure(image=photo)
                        preview_label.image = photo
                        select_btn = tk.Button(preview_label, text="Select", 
                                             command=lambda f=filename: update_background(f))
                        select_btn.place(relx=1.0, rely=0, anchor='ne')

                def update_background(filename):
                    def load_background():
                        loading_label = tk.Label(root, text="Loading...", 
                                               font=("Arial", 20), bg='black', fg='white')
                        loading_label.place(relx=0.5, rely=0.5, anchor="center")
                        root.update()

                        bg_path = os.path.join(os.path.dirname(__file__), "img", "background", filename)
                        image = Image.open(bg_path)
                        
                        for widget in root.winfo_children():
                            if isinstance(widget, tk.Canvas) and widget != root.settings_canvas:
                                widget.delete('all')
                                if hasattr(widget, 'is_animating'):
                                    delattr(widget, 'is_animating')
                                
                                if filename.endswith('.gif') and A_Animate:
                                    frames = []
                                    try:
                                        while True:
                                            resized = image.resize((root.winfo_screenwidth(), root.winfo_screenheight()), 
                                                                 Image.Resampling.LANCZOS)
                                            frames.append(ImageTk.PhotoImage(resized))
                                            image.seek(len(frames))
                                    except EOFError:
                                        pass
                                    
                                    widget.frames = frames
                                    widget.is_animating = True
                                    animate_gif(widget, frames)
                                else:  
                                    resized = image.resize((root.winfo_screenwidth(), root.winfo_screenheight()), 
                                                         Image.Resampling.LANCZOS)
                                    bg = ImageTk.PhotoImage(resized)
                                    widget.create_image(0, 0, image=bg, anchor="nw")
                                    widget.image = bg

                        loading_label.destroy()

                    thread = threading.Thread(target=load_background)
                    thread.daemon = True
                    thread.start()

                def change_preview(direction):
                    current_preview["index"] = (current_preview["index"] + direction) % len(bg_files)
                    show_preview(bg_files[current_preview["index"]])

                if bg_files:
                    show_preview(bg_files[current_preview["index"]])

            update_background_list()

            def myra(is_on=False, checkstatus=False): #detta är bara för min klasskamrat frågade efter det ;)
                global myra 
                if checkstatus:
                    return myra
                myra = is_on
                def update_myra(posx=0, posy=0, rot=0):
                    if myra:
                        image_path = os.path.join(os.path.dirname(__file__), "img", "icons", "myr-3.png")
                        try:
                            ant_image = ImageTk.PhotoImage(Image.open(image_path).resize((50, 50), Image.Resampling.LANCZOS))
                        except FileNotFoundError:
                            ant_image = None

                        if ant_image:
                            if hasattr(root, 'ant_label'):
                                root.ant_label.destroy()
                            root.ant_label = tk.Label(root, image=ant_image, bg='#a0a0a0')
                            root.ant_label.image = ant_image
                            root.ant_label.place(x=posx, y=posy)

                            def move_ant():
                                try:
                                    if myra:
                                        nonlocal posx, posy, rot
                                        if not hasattr(root, 'target_x'):
                                            root.target_x = random.randint(0, root.winfo_width() - 30)
                                            root.target_y = random.randint(0, root.winfo_height() - 30)

                                        speed = 1
                                        dx = root.target_x - posx
                                        dy = root.target_y - posy
                                        dist = (dx**2 + dy**2)**0.5

                                        if dist > 10:
                                            dx = dx/dist * speed
                                            dy = dy/dist * speed
                                            posx += dx
                                            posy += dy
                                            rot = -90 + (180/3.14159) * (2.718282 if dy == 0 else (dy/dx if dx != 0 else 1.57))
                                        else:
                                            root.target_x = random.randint(0, root.winfo_width() - 30)
                                            root.target_y = random.randint(0, root.winfo_height() - 30)

                                        posx = max(0, min(posx, root.winfo_width() - 30))
                                        posy = max(0, min(posy, root.winfo_height() - 30))
                                        
                                        img = Image.open(image_path).convert('RGBA')
                                        data = img.getdata()
                                        newData = []
                                        for item in data:
                                            if item[0] > 240 and item[1] > 240 and item[2] > 240:
                                                newData.append((255, 255, 255, 0))
                                            else:
                                                newData.append(item)
                                        img.putdata(newData)
                                        img = img.resize((30, 30), Image.Resampling.LANCZOS).rotate(rot)
                                        ant_image = ImageTk.PhotoImage(img)
                                        root.ant_label.configure(image=ant_image)
                                        root.ant_label.image = ant_image
                                        root.ant_label.place(x=posx, y=posy)
                                        
                                        root.after(30, move_ant)
                                    else:
                                        root.ant_label.destroy()
                                except:
                                    pass
                            root.update_idletasks()
                            move_ant()
                if myra:
                    update_myra()

            create_toggle(30, 150, myra, "myra?", root.settings_canvas)

            def rainbow_toggle(is_on=False, checkstatus=False):
                global Rainbow
                if checkstatus:
                    return Rainbow
                Rainbow = is_on
                save_state({"searches": searches, "rainbow": is_on})
                toggle_lights()
            
            def rainbow_backround_allow_lights(is_on=False, checkstatus=False):
                global a_light_sleep
                if checkstatus:
                    return a_light_sleep
                a_light_sleep = is_on
                save_state({"searches": searches, "rainbow": Rainbow, "a_light_sleep": is_on})


            root.update_idletasks()
            create_toggle(root.settings_canvas.winfo_width()-(root.settings_canvas.winfo_width() * (29.20 / 100)), 150, rainbow_toggle, "rainbow lights", root.settings_canvas)
            create_toggle(root.settings_canvas.winfo_width()-(root.settings_canvas.winfo_width() * (29.20 / 100)), 200, rainbow_backround_allow_lights, "rainbow background att sleep", root.settings_canvas)
            sleep_button = tk.Button(root.settings_canvas, text="sleep", command=lambda: sleep_animation(root, start_idle_timer), font=("Arial", 12), bg='#808080', fg='white')
            sleep_button.place(x=root.settings_canvas.winfo_width()-(root.settings_canvas.winfo_width() * (29.20 / 100)), y = 255)
            def check_connected_network():
                def get_network_info():
                    try:
                        if os.name == 'nt': 
                            result = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], capture_output=True, text=True)
                            current = [line.split(':')[1].strip() for line in result.stdout.split('\n') if 'SSID' in line and 'BSSID' not in line]
                            
                            result = subprocess.run(['netsh', 'wlan', 'show', 'profiles'], capture_output=True, text=True)
                            networks = [line.split(':')[1].strip() for line in result.stdout.split('\n') if 'All User Profile' in line]
                            
                            return current[0] if current else "Not connected", networks
                            
                        else:  
                            result = subprocess.run(['iwgetid', '-r'], capture_output=True, text=True)
                            current = result.stdout.strip()
                            
                            result = subprocess.run(['nmcli', '-g', 'NAME', 'connection', 'show'], capture_output=True, text=True)
                            networks = result.stdout.strip().split('\n')
                            
                            return current if current else "Not connected", networks
                            
                    except Exception as e:
                        return "Error detecting network", []

                current_network, saved_networks = get_network_info()
                network_frame = tk.Frame(root.settings_canvas, bg='#a0a0a0')
                network_frame.place(x=section_width + 50, y=150)

                list_width = int((section_width - 100) / 8)  
                
                current_label = tk.Label(network_frame, text=f"Connected to: {current_network}",
                                       font=("Arial", 14), bg='#a0a0a0', fg='black',
                                       wraplength=section_width-100)
                current_label.pack(pady=5)

                list_frame = tk.Frame(network_frame, bg='#505050')
                list_frame.pack(pady=5)

                scrollbar = tk.Scrollbar(list_frame)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

                network_list = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                        width=list_width, height=10,
                                        bg='#505050', fg='white',
                                        selectmode=tk.SINGLE)
                network_list.pack(side=tk.LEFT)

                scrollbar.config(command=network_list.yview)

                for network in saved_networks:
                    network_list.insert(tk.END, network)
            check_connected_network()
                        

                

    def main():
        root.update_idletasks()
        image_path = os.path.join(os.path.dirname(__file__), "img", "background", "main-background.png")
        screen_width, screen_height = root.winfo_screenwidth(), root.winfo_screenheight()
        bg_image = ImageTk.PhotoImage(Image.open(image_path).resize((screen_width, screen_height), Image.Resampling.LANCZOS))

        canvas = tk.Canvas(root, width=screen_width, height=screen_height, highlightthickness=0)
        canvas.place(x=0, y=0, relwidth=1, relheight=1)
        canvas.create_image(0, 0, image=bg_image, anchor="nw")
        root.image = bg_image

        button_style = {
            'font': ('Helvetica', 12, 'bold'),
            'bg': '#808080',
            'fg': 'white',
            'width': 10,
            'height': 1,
            'relief': 'flat',
            'borderwidth': 0,
            'highlightthickness': 0,
            'bd': 0,
            'activebackground': '#a0a0a0'
        }

        def create_rounded_button(parent, **kwargs):
            button = tk.Button(parent, **kwargs)
            button.configure(relief="flat", overrelief="flat")
            button.configure(highlightbackground='#808080', highlightcolor='#808080', highlightthickness=1)
            button.configure(borderwidth=0)
            button.configure(padx=10, pady=5)
            return button

        def on_enter(e):
            e.widget['background'] = '#a0a0a0'

        def on_leave(e):
            e.widget['background'] = '#808080'

        home_button = create_rounded_button(root, text="Home", command=lambda: messagebox.showinfo("Home button", "you are already here? are you not?"), **button_style)
        home_button.bind("<Enter>", on_enter)
        home_button.bind("<Leave>", on_leave)
        home_button.place(x=10, y=10)

        settings_button = create_rounded_button(root, text="Settings", command=lambda: settings(), **button_style)
        settings_button.bind("<Enter>", on_enter)
        settings_button.bind("<Leave>", on_leave)
        settings_button.place(x=10, y=40)

        admin_button = create_rounded_button(root, text="Admin", command=lambda: messagebox.showwarning("nej", "du får inte!"), **button_style)
        admin_button.bind("<Enter>", on_enter)
        admin_button.bind("<Leave>", on_leave)
        admin_button.place(x=10, y=70)
        
        search_entry = tk.Entry(root, width=30, font=("Arial", 20))
        search_entry.configure(relief="flat")
        search_entry.configure(bg='#3a3840', fg='white', insertbackground='white')
        search_entry.place(relx=0.5, y=100, anchor="center")

        def on_search(event=None):
            searchphrase = search_entry.get()
            search_data(searchphrase)

        search_entry.bind("<KeyRelease>", on_search)

        search_entry.configure(highlightbackground='#3a3840', highlightcolor='#3a3840', highlightthickness=1)
        search_entry.configure(borderwidth=0)

        search_history_title = tk.Label(root, text="Active Searches", width=15, font=("Arial", 16), bg='#808080', fg='white')
        search_history_title.place(x=screen_width - 200, y=150)
        
        def clear_searches():
            global searches, allow_searches
            if not allow_searches:
                messagebox.showerror("Error - blocked by admin", "clearing is disabled by admin")
                return
            searches = []
            save_state({"searches": searches, "rainbow": Rainbow})  
            update_searches()
            searchphrase = search_entry.get()
            search_data(searchphrase)
            toggle_lights()
        clear_button = create_rounded_button(root, text="Clear Searches", command=lambda: clear_searches(), **button_style)
        clear_button.bind("<Enter>", on_enter)
        clear_button.bind("<Leave>", on_leave)
        clear_button.place(x=screen_width - 165, y=110)

        periodic_update()

    main()
    root.mainloop()

def start_web_server():
    try:
        from webpage import app
        app.run(host='0.0.0.0', port=80, debug=False)
    except Exception as e:
        fail_warning(e)

def fail_warning(e="unkownn error"):
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"CRITICAL ERROR: {str(e)}")
        with open("error.log", "a") as f:
            f.write(f"{timestamp}::CRITICAL ERROR: {str(e)}\n")
        
        def warning_loop():
            while True:
                try:
                    import board
                    import neopixel
                    

                    pixel_pin = board.D18
                    num_pixels = 360
                    ORDER = neopixel.GRB
                    pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=1.0, auto_write=False, pixel_order=ORDER)
                    
                    for _ in range(3):
                        pixels.fill((255, 0, 0))  
                        pixels.show()
                        time.sleep(0.5)
                        pixels.fill((0, 0, 0))    
                        pixels.show() 
                        time.sleep(0.5)
                    
                    time.sleep(2)  
                except Exception as e:
                    print("Warning:  ", str(e))
                    time.sleep(3)

        warning_thread = threading.Thread(target=warning_loop)
        warning_thread.start()
        messagebox.showwarning("Critical error", e)
        messagebox.showinfo("Potential solution", "Please restart the system to automatically attempt to fix the error \n if auto fix failed download original copy from github \n 'https://github.com/Oscar-Johannesson/T11-Storage'")
    


if __name__ == "__main__":
    try:
        server_thread = threading.Thread(target=start_web_server)
        server_thread.daemon = True 
        server_thread.start()
        
        main_ui()
        
    except Exception as e:
        
        fail_warning(e)
