import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import requests 
import threading
import chess
import re
from bs4 import BeautifulSoup 
import os
from PIL import Image, ImageTk
import math
import time
import random

class DumenApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dümen Dünyam - Satranç Dümeni")
        self.root.geometry("1280x720")  # Increased window size for better visibility
        self.root.minsize(800, 800)
        self.game_id = None
        self.username = None
        self.board = chess.Board()
        self.movable_pieces = []
        
        # Store the image reference to prevent garbage collection
        self.wheel_image = None
        self.wheel_image_original = None
        self.wheel_images_cache = {}  # Cache for rotated images
        self.arrow_image = None
        
        # Animation settings
        self.animation_duration = 5000  # 5 seconds in milliseconds
        self.animation_start_time = 0  # Track when animation starts
        self.is_animating = False
        self.current_angle = 0
        self.rotation_count = 0
        self.target_rotations = 3
        
        # All possible piece names allow multiple
        #define globally
        global allowMultiplePiece
        allowMultiplePiece = True
        
        # Settings
        self.settings = {
            "rotation_time": 5  # Default 5 seconds
        }
        
        # Set modern theme
        self.set_theme()
        
        # Setup UI
        self.setup_ui()
        
        # Preload the wheel image immediately
        self.preload_wheel_image()
        
    def set_theme(self):
        style = ttk.Style()
        style.theme_use('clam')  # Use a modern base theme
        
        # Configure styles for various elements
        style.configure("TButton", 
                       font=("Arial", 12),
                       padding=10,
                       background="#4CAF50",
                       foreground="white")
        
        style.configure("Settings.TButton",
                       font=("Arial", 12),
                       padding=8,
                       background="#2196F3",
                       foreground="white")
                       
        style.configure("TurnWheel.TButton", 
                       font=("Arial", 14, "bold"),
                       padding=12,
                       background="#FF5722",
                       foreground="white")
                       
        style.map("TButton", 
                 background=[("active", "#66BB6A")],
                 foreground=[("active", "white")])
                 
        style.map("Settings.TButton", 
                 background=[("active", "#42A5F5")],
                 foreground=[("active", "white")])
                 
        style.map("TurnWheel.TButton", 
                 background=[("active", "#FF7043")],
                 foreground=[("active", "white")])
        
    def setup_ui(self):
        # Create frames
        input_frame = ttk.Frame(self.root, padding="10")
        input_frame.pack(fill=tk.X)
        
        # Main content frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)
        
        # Username input
        ttk.Label(input_frame, text="Lichess Kullanıcı Adı:").pack(side=tk.LEFT)
        self.username_entry = ttk.Entry(input_frame, width=30)
        self.username_entry.pack(side=tk.LEFT, padx=5)
        
        # Fetch button
        self.fetch_btn = ttk.Button(input_frame, text="Kullanıcı adını seç", command=self.set_username)
        self.fetch_btn.pack(side=tk.LEFT, padx=5)
        
        # Settings button
        self.settings_btn = ttk.Button(
            input_frame, 
            text="⚙️ Ayarlar", 
            command=self.open_settings,
            style="Settings.TButton"
        )
        self.settings_btn.pack(side=tk.LEFT, padx=5)

        # Status label
        self.status_var = tk.StringVar(value="Enter a Lichess username and click 'Set Username'")
        status_label = ttk.Label(input_frame, textvariable=self.status_var)
        status_label.pack(side=tk.RIGHT, padx=5)
        
        # Create a central container for the wheel and result
        wheel_container = ttk.Frame(main_frame)
        wheel_container.pack(expand=True, fill=tk.BOTH)
        
        # Canvas for wheel - keep it centered
        self.canvas = tk.Canvas(wheel_container, height=500, width=500, bg="white")
        self.canvas.pack(expand=True)
        
        # Wait for the canvas to be properly sized before displaying the wheel
        self.root.update_idletasks()
        
        # Result label - directly under the wheel
        self.result_var = tk.StringVar()
        self.result_label = ttk.Label(wheel_container, textvariable=self.result_var, font=("Arial", 18, "bold"))
        self.result_label.pack(pady=10)
        
        # "Turn the Wheel" button - at the bottom of wheel container
        self.turn_wheel_btn = ttk.Button(
            wheel_container, 
            text="Dümeni Çevir", 
            command=self.turn_wheel,
            style="TurnWheel.TButton"
        )
        self.turn_wheel_btn.pack(pady=10)
        
        # Load the arrow image
        try:
            arrow_path = os.path.join(os.path.dirname(__file__), "arrow.png")
            if not os.path.exists(arrow_path):
                # Create a simple arrow if image doesn't exist
                self.create_arrow_image()
                arrow_path = os.path.join(os.path.dirname(__file__), "arrow1.png")
            
            arrow_img = Image.open(arrow_path)
            arrow_img = arrow_img.resize((50, 60))  # Resize as needed
            self.arrow_image = ImageTk.PhotoImage(arrow_img)
        except Exception as e:
            print(f"Error loading arrow image: {e}")
            self.arrow_image = None

    def create_arrow_image(self):
        """Create a simple arrow image if one doesn't exist"""
        from PIL import Image, ImageDraw
        
        # Create a new image with a transparent background
        img = Image.new('RGBA', (100, 60), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw a simple triangle arrow
        draw.polygon([(0, 20), (0, 40), (80, 30)], fill=(255, 0, 0, 255))
        
        # Save the image
        img_path = os.path.join(os.path.dirname(__file__), "arrow.png")
        img.save(img_path)

    def set_username(self):
        """Set the username for fetching game data"""
        self.username = self.username_entry.get().strip()
        if not self.username:
            messagebox.showerror("Error", "Lichess kullanıcı adınızı girin.")
            return
        
        self.status_var.set(f"Dümen hazır. {self.username}")
        
    def turn_wheel(self):
        """Fetch current game data and turn the wheel"""
        if not self.username:
            messagebox.showerror("Error", "Dümeni çevirmek için Lichess kullanıcı adınızı girin.")
            return
        
        if self.is_animating:
            return
            
        self.status_var.set(f"Oyun verisi {self.username} için alınıyor...")
        # Start in a thread to avoid freezing UI
        threading.Thread(target=self.fetch_game_data, daemon=True).start()
    
    def fetch_game_data(self):
        """
        Fetch the current game data and process it
        """
        try:
            # Step 1: Get current game ID from API
            api_url = f"https://lichess.org/api/user/{self.username}/current-game"
            
            headers = {
                'User-Agent': 'DumenDunyam/1.0 (Chess piece roulette app)'
            }
            
            # Fetch API data to get game ID
            api_response = requests.get(api_url, headers=headers, timeout=10)
            
            if api_response.status_code == 200:
                # Extract game ID from the PGN data
                game_data = api_response.text
                game_id_match = re.search(r'\[GameId "([^"]+)"\]', game_data)
                
                if game_id_match:
                    self.game_id = game_id_match.group(1)
                    
                    # Step 2: Now fetch the HTML page for this game
                    game_url = f"https://lichess.org/{self.game_id}"
                    #print(f"Game url: {game_url}")
                    self.status_var.set(f"Getting game page: {self.game_id}")
                    
                    html_response = requests.get(game_url, headers=headers, timeout=10)
                    
                    if html_response.status_code == 200:
                        # Step 3: Extract the PGN data and process it
                        fen_text = self.extract_fen(html_response.text)
                        if fen_text:
                            # Process the PGN to get FEN and legal moves
                            self.process_fen(fen_text)
                        else:
                            self.status_var.set("Oyun verisi alınamadı.")
                    else:
                        self.status_var.set(f"Oyun verisi alınırken hata oluştu.: {html_response.status_code}")
                else:
                    self.status_var.set(f"Aktif oyun {self.username} için bulunamadı.")
            else:
                self.status_var.set(f"API Error: {api_response.status_code}")
                
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda msg=error_msg: self.status_var.set(f"Error: {msg}"))

    def extract_fen(self, html_content):
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Find the script tag containing page-init-data
            script_tag = soup.select_one('script#page-init-data')

            if not script_tag:
                return None
            
            # get last fen value
            fen = script_tag.get_text().split('"fen":"')[-1].split('"')[0]
            print(fen)

            if not fen:
                return None

            return fen
            
        except Exception as e:
            self.status_var.set(f"Error extracting PGN: {str(e)}")
            return None

    def process_fen(self, fen):
        try:
            
            # Create a new board with the FEN
            self.board = chess.Board(fen)
            
            # Get all legal moves
            legal_moves = list(self.board.legal_moves)
            
            # Extract unique pieces that can move
            piece_map = self.board.piece_map()
            movable_pieces = []
            piece_names = {
                chess.PAWN: "Piyon",
                chess.KNIGHT: "At",
                chess.BISHOP: "Fil",
                chess.ROOK: "Kale",
                chess.QUEEN: "Vezir",
                chess.KING: "Şah"
            }
            
            # Determine whose turn it is
            turn_color = self.board.turn
            print(f"Turn color: {turn_color}")

            # Find all pieces that can move
            for move in legal_moves:
                # Get the square the move is from
                from_square = move.from_square
                 # Check if the piece is of the current player
                if from_square in piece_map:
                    # Get the piece object
                    piece = piece_map[from_square]
                    # Check if the piece belongs to the current player
                    if piece.color == turn_color:
                        # Get the piece name
                        piece_name = piece_names[piece.piece_type]
                        # Add the piece name if not already in the list
                        if piece_name not in movable_pieces:
                            # Add the piece name
                            movable_pieces.append(piece_name)
            
            self.movable_pieces = movable_pieces
            
            
            if turn_color:
                turn_color = "Beyaz"                
                
            else:
                turn_color = "Siyah"
                

            #print(f"Color of the pieces: {turn_color}")
            #print(f"Movable pieces: {movable_pieces}")
            if movable_pieces:
                # Pre-load the wheel image to prevent UI lag
                #self.preload_wheel_image()
                # Use a small delay to allow UI to update
                self.root.after(100, lambda: self.spin_wheel(movable_pieces))
            else:
                self.result_var.set("No pieces can move!")
        
        except Exception as e:
            self.status_var.set(f"Error processing FEN: {str(e)}")

    def open_settings(self):
        """Open settings dialog"""
        settings_dialog = tk.Toplevel(self.root)
        settings_dialog.title("Ayarlar")
        settings_dialog.geometry("400x300")
        settings_dialog.transient(self.root)  # Make dialog modal
        settings_dialog.grab_set()
        
        # Center the dialog on parent window
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (400 // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (300 // 2)
        settings_dialog.geometry(f"+{x}+{y}")
        
        # Create a frame with padding
        frame = ttk.Frame(settings_dialog, padding="20")
        frame.pack(expand=True, fill=tk.BOTH)
        
        # Rotation time slider
        ttk.Label(frame, text="Dümen Dönüş Süresi (saniye):", font=("Arial", 12)).pack(pady=10)
        
        rotation_scale = ttk.Scale(
            frame, 
            from_=1, 
            to=10, 
            orient=tk.HORIZONTAL, 
            length=300,
            value=self.settings["rotation_time"]
        )
        rotation_scale.pack(pady=10)
        
        # Value label
        value_var = tk.StringVar(value=f"{self.settings['rotation_time']} saniye")
        value_label = ttk.Label(frame, textvariable=value_var, font=("Arial", 14, "bold"))
        value_label.pack(pady=10)
        
        # Update value label when slider moves
        def update_value(event):
            value = round(rotation_scale.get())
            value_var.set(f"{value} saniye")
        
        rotation_scale.bind("<Motion>", update_value)
        
        # Save button
        def save_settings():
            self.settings["rotation_time"] = round(rotation_scale.get())
            self.animation_duration = self.settings["rotation_time"] * 1000
            settings_dialog.destroy()
        
        ttk.Button(
            frame, 
            text="Kaydet", 
            command=save_settings,
            style="TButton"
        ).pack(pady=20)

    def preload_wheel_image(self):
        """Load the wheel image and prepare it for animation"""
        try:
            # Look for dumen.png in the same directory as the script
            wheel_path = os.path.join(os.path.dirname(__file__), "dumen.png")
            
            # Check if file exists
            if not os.path.exists(wheel_path):
                # Create a simple wheel if image doesn't exist
                self.create_default_wheel()
                wheel_path = os.path.join(os.path.dirname(__file__), "dumen.png")
            
            # Load the image
            original_image = Image.open(wheel_path)

            # Determine size based on canvas
            wheel_size = 300  # Fixed size for better performance
            
            # Resize the image
            resized_image = original_image.resize((wheel_size, wheel_size))
            self.wheel_image_original = resized_image
            self.wheel_image = ImageTk.PhotoImage(resized_image)
            
            # Allow UI to update and properly size
            self.root.update_idletasks()
            
            # Display the wheel immediately
            self.display_initial_wheel()
            
            self.status_var.set("Dümen resmi yüklendi. Çevirmeye hazır.")
            
        except Exception as e:
            error_msg = f"Dümen resmi yüklenirken hata oluştu: {str(e)}"
            self.status_var.set(error_msg)
    
    def display_initial_wheel(self):
        """Display the initial wheel on the canvas"""
        # Clear the canvas
        self.canvas.delete("all")
        
        # Get canvas dimensions and ensure they're valid
        self.root.update_idletasks()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width < 100:  # If canvas not yet properly sized
            canvas_width = 600
        if canvas_height < 100:
            canvas_height = 600
        
        # Calculate center position
        center_x = canvas_width // 2
        center_y = canvas_height // 2
        
        # Display the wheel
        if self.wheel_image:
            self.canvas.create_image(center_x, center_y, image=self.wheel_image, tags=("wheel",))
            
            # Place the arrow on the right side
            if self.arrow_image:
                arrow_x = center_x + (self.wheel_image.width() // 2) + 100
                arrow_y = center_y
                self.canvas.create_image(arrow_x, arrow_y, image=self.arrow_image, tags=("arrow",))
            else:
                # Create a simple arrow if image is not available
                arrow_x = center_x + (self.wheel_image.width() // 2) + 30
                arrow_y = center_y
                self.canvas.create_polygon(
                    arrow_x, arrow_y-15, 
                    arrow_x+30, arrow_y, 
                    arrow_x, arrow_y+15, 
                    fill="red", 
                    outline="black",
                    tags=("arrow",)
                )

    def spin_wheel(self, pieces):
        """Start the wheel spinning animation"""
        if self.is_animating:
            return
            
        # Reset any previous result
        self.result_var.set("")
        
        # Clear the canvas
        self.canvas.delete("all")
        
        # Draw the wheel in its initial position
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        center_x = canvas_width // 2
        center_y = canvas_height // 2
        
        # Place the wheel image
        wheel_id = self.canvas.create_image(center_x, center_y, image=self.wheel_image, tags=("wheel",))
        
        # Place the arrow on the right side
        if self.arrow_image:
            arrow_x = center_x + (self.wheel_image.width() // 2) + 100
            arrow_y = center_y
            self.canvas.create_image(arrow_x, arrow_y, image=self.arrow_image, tags=("arrow",))
        else:
            # Create a simple arrow if image is not available
            arrow_x = center_x + (self.wheel_image.width() // 2) + 30
            arrow_y = center_y
            self.canvas.create_polygon(
                arrow_x, arrow_y-15, 
                arrow_x+30, arrow_y, 
                arrow_x, arrow_y+15, 
                fill="red", 
                outline="black",
                tags=("arrow",)
            )
        
        # Calculate positions for pieces around the wheel
        self.position_pieces_around_wheel(pieces, center_x, center_y)
        
        # Start animation
        self.is_animating = True
        self.animation_start_time = time.time() * 1000  # Current time in ms
        self.current_angle = 0
        self.rotation_count = 0
        self.animate_wheel()

    def position_pieces_around_wheel(self, pieces, center_x, center_y):
        """Position piece names around the wheel"""
        if not pieces:
            return
            
        # Get wheel radius
        wheel_radius = self.wheel_image.width() // 2
        
        # Calculate positions for pieces
        num_pieces = len(pieces)
        angle_step = 360 / num_pieces
        
        # Store piece positions for animation
        self.piece_positions = []
        
        # Create text items for each piece
        for i, piece in enumerate(pieces):
            angle = i * angle_step
            radians = math.radians(angle)
            
            # Position text outside the wheel
            text_radius = wheel_radius + 40

            x = center_x + int(text_radius * math.cos(radians))
            y = center_y + int(text_radius * math.sin(radians))
            
            # Create text with a unique tag
            text_id = self.canvas.create_text(
                x, y, 
                text=piece,
                font=("Arial", 16, "bold"),
                fill="black",
                angle=-angle,  # Counter-rotate text to keep it readable
                tags=(f"piece_{i}", "piece")
            )
            
            # Store position info for animation
            self.piece_positions.append({
                "id": text_id,
                "angle": angle,
                "radius": text_radius
            })

    def animate_wheel(self):
        """Animate the wheel rotation with improved easing"""
        if not self.is_animating:
            return
            
        # Calculate the elapsed time
        current_time = time.time() * 1000
        elapsed = current_time - self.animation_start_time
        
        # Check if animation should end
        if elapsed >= self.animation_duration:
            self.finish_animation()
            return

        # Calculate rotation angle with improved easing
        progress = elapsed / self.animation_duration
        
        # Calculate easing factor with more dramatic slowdown at the end
        # Use a combination of easeOutCubic and easeOutQuint for better visual effect
        if progress < 0.7:  # First 70% of animation - more constant speed
            eased_progress = 0.7 * progress / 0.7
        else:  # Last 30% - dramatic slowdown
            p = (progress - 0.7) / 0.3  # Normalize to 0-1 range for this segment
            # More pronounced slowdown curve
            eased_progress = 0.7 + 0.3 * (1 - (1 - p) ** 5)
        
        # Ensure we rotate exactly target rotations plus a random ending position
        total_rotations = self.target_rotations + (random.random() * 0.8 + 0.1)  # Random final position
        target_angle = total_rotations * 360 * eased_progress
        
        # Update the wheel rotation
        self.rotate_wheel_to_angle(target_angle)
        
        # Check if we've completed another rotation
        current_rotation = int(target_angle / 360)
        if current_rotation > self.rotation_count:
            self.rotation_count = current_rotation
            # Show intermediate result if not the final rotation
            #

        # Schedule next frame with optimal framerate
        self.root.after(16, self.animate_wheel)  # ~60 FPS

    def rotate_wheel_to_angle(self, angle):
        """Rotate the wheel to the specified angle"""
        # Only cache key angles for better performance
        cache_key = int(angle / 10) * 10  # Cache every 10 degrees
        if cache_key in self.wheel_images_cache:
            rotated_image = self.wheel_images_cache[cache_key]
        else:
            # Rotate the original image
            rotated_img = self.wheel_image_original.rotate(-angle)  # Negative for clockwise rotation
            rotated_image = ImageTk.PhotoImage(rotated_img)
            
            # Only cache if it's a key angle
            if angle % 10 < 0.1:  # Only cache at 10-degree intervals
                self.wheel_images_cache[cache_key] = rotated_image
        
        # Update wheel image
        self.canvas.itemconfig("wheel", image=rotated_image)
        # Keep a reference to prevent garbage collection
        self.wheel_image = rotated_image
        
        # Update piece positions
        self.update_piece_positions(angle)

    def update_piece_positions(self, angle):
        """Update the positions of pieces based on wheel rotation"""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        center_x = canvas_width // 2
        center_y = canvas_height // 2
        
        for pos in self.piece_positions:
            # Calculate new position based on updated angle
            new_angle = pos["angle"] + angle
            radians = math.radians(new_angle)
            
            x = center_x + int(pos["radius"] * math.cos(radians))
            y = center_y + int(pos["radius"] * math.sin(radians))
            
            # Update text position and rotation
            self.canvas.coords(pos["id"], x, y)
            self.canvas.itemconfig(pos["id"], angle=-new_angle)  # Counter-rotate text

    def finish_animation(self):
        """Finish the wheel animation and determine the result"""
        
        self.is_animating = False
        # Find which piece is at the arrow position
        result = self.determine_selected_piece()

        
        if result:
            # Get the turn color
            turn_color = "Beyaz" if self.board.turn else "Siyah"
            
            # Display the result
            result_text = f"{turn_color} TAŞ: {result.upper()}"
            self.result_var.set(result_text)
            
            # Highlight the result
            self.result_label.configure(foreground="#FF5722")
        else:
            self.result_var.set("Sonuç belirlenemedi!")

    def determine_selected_piece(self):
        """Determine which piece is at the arrow position"""
        try:
            # Get arrow position
            arrow_item = self.canvas.find_withtag("arrow")
            if not arrow_item:
                return None
                
            arrow_x, arrow_y = self.canvas.coords(arrow_item[0])
            
            # Find the nearest piece to the arrow
            nearest_piece = None
            min_distance = float('inf')
            
            for pos in self.piece_positions:
                piece_id = pos["id"]
                piece_x, piece_y = self.canvas.coords(piece_id)
                
                # Calculate distance
                distance = math.sqrt((piece_x - arrow_x) ** 2 + (piece_y - arrow_y) ** 2)
                
                # Update nearest if closer
                if distance < min_distance:
                    min_distance = distance
                    nearest_piece = piece_id
            
            if nearest_piece:
                piece_text = self.canvas.itemcget(nearest_piece, "text")
                return piece_text
        
        except Exception as e:
            print(f"Error determining selected piece: {e}")
        
        return None

def main():
    root = tk.Tk()
    app = DumenApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
