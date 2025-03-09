import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import requests 
import threading
import chess
import re
from bs4 import BeautifulSoup 

class DumenApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dümen Dünyam - Satranç Dümeni")
        self.root.geometry("1280x720")  # Increased window size for better visibility
        self.game_id = None
        self.username = None
        self.board = chess.Board()
        self.movable_pieces = []
        
        # Store the image reference to prevent garbage collection
        self.wheel_image = None
        self.wheel_image_original = None
        self.wheel_images_cache = {}  # Cache for rotated images
        
        # Animation settings
        self.animation_duration = 5000  # 5 seconds in milliseconds
        self.animation_frames_skip = 3  # Skip frames to improve performance
        self.animation_start_time = 0  # Track when animation starts
        
        # All possible piece names allow multiple
        #define globally
        global allowMultiplePiece
        allowMultiplePiece = True
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        # Create frames
        input_frame = ttk.Frame(self.root, padding="10")
        input_frame.pack(fill=tk.X)
        
        wheel_frame = ttk.Frame(self.root, padding="10")
        wheel_frame.pack(expand=True, fill=tk.BOTH)
        
        # Username input
        ttk.Label(input_frame, text="Lichess Kullanıcı Adı:").pack(side=tk.LEFT)
        self.username_entry = ttk.Entry(input_frame, width=30)
        self.username_entry.pack(side=tk.LEFT, padx=5)
        
        # Fetch button
        self.fetch_btn = ttk.Button(input_frame, text="Kullanıcı adını seç", command=self.set_username)
        self.fetch_btn.pack(side=tk.LEFT, padx=5)
        
        # "Turn the Wheel" button
        self.turn_wheel_btn = ttk.Button(
            wheel_frame, 
            text="Turn the Wheel", 
            command=self.turn_wheel,
            style="TurnWheel.TButton"
        )
        self.turn_wheel_btn.place(relx=0.5, rely=0.9, anchor="center")
        
        # Create custom style for the button
        button_style = ttk.Style()
        button_style.configure("TurnWheel.TButton", font=("Arial", 14, "bold"))
        
        # Status label
        self.status_var = tk.StringVar(value="Enter a Lichess username and click 'Set Username'")
        status_label = ttk.Label(input_frame, textvariable=self.status_var)
        status_label.pack(side=tk.RIGHT, padx=5)
        
        # Canvas for wheel
        self.canvas = tk.Canvas(wheel_frame, bg="white")
        self.canvas.pack(expand=True, fill=tk.BOTH)
        
        # Result label
        self.result_var = tk.StringVar()
        result_label = ttk.Label(wheel_frame, textvariable=self.result_var, font=("Arial", 16))
        result_label.pack(pady=10)       

    def set_username(self):
        """Set the username for fetching game data"""
        self.username = self.username_entry.get().strip()
        if not self.username:
            messagebox.showerror("Error", "Lichess kullanıcı adınızı girin.")
            return
        
        self.status_var.set(f"Kullanıcı adı: {self.username}. Dümeni çevirmek için hazır.")
        
    def turn_wheel(self):
        """Fetch current game data and turn the wheel"""
        if not self.username:
            messagebox.showerror("Error", "Dümeni çevirmek için Lichess kullanıcı adınızı girin.")
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
                    print(f"Game url: {game_url}")
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
            # Update status
            self.status_var.set(f"Processing FEN: {fen}")
            
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
                

            print(f"Color of the pieces: {turn_color}")
            print(f"Movable pieces: {movable_pieces}")
            if movable_pieces:
                # Pre-load the wheel image to prevent UI lag
                self.preload_wheel_image()
                # Use a small delay to allow UI to update
                self.root.after(100, lambda: self.spin_wheel(movable_pieces))
            else:
                self.result_var.set("No pieces can move!")
        
        except Exception as e:
            self.status_var.set(f"Error processing FEN: {str(e)}")

def main():
    root = tk.Tk()
    app = DumenApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
