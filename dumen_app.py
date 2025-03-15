"""
Dümen Dünyam - Satranç Taş Seçim Dümeni Uygulaması

Bu uygulama, Lichess'te aktif satranç oyunu oynayan kullanıcıların,
oyunlarında hangi taşı oynayacaklarını rastgele belirleyen eğlenceli
bir dümen sistemi sunar.

Geliştirici: brnceran
Versiyon: 1.0
"""
import sys
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
    """
    Dümen Dünyam uygulamasının ana sınıfı.
    
    Bu sınıf, kullanıcı arayüzünü oluşturur, Lichess API ile iletişim kurar
    ve satranç taşı seçimi için dümen animasyonunu yönetir.
    """
    def __init__(self, root):
        """
        Uygulama arayüzünü ve bileşenlerini başlatır.
        
        Parametreler:
            root: Tkinter ana penceresi
        """
        self.root = root
        self.root.title("Dümen Dünyam - Satranç Dümeni")
        self.root.geometry("1280x720")  # Daha iyi görünürlük için genişletilmiş pencere boyutu
        self.root.minsize(800, 800)  # Minimum pencere boyutu
        
        # Oyun verileri için gerekli değişkenleri başlat
        self.game_id = None  # Aktif oyunun ID'si
        self.username = None  # Lichess kullanıcı adı
        self.board = chess.Board()  # Satranç tahtası
        self.movable_pieces = []  # Hareket edebilecek taşların listesi
        
        # Görsel referanslarını çöp toplayıcının silmemesi için sakla
        self.wheel_image = None  # Dümen görüntüsü
        self.wheel_image_original = None  # Orijinal dümen görüntüsü
        self.wheel_images_cache = {}  # Döndürülmüş görüntüler için önbellek
        self.arrow_image = None  # Ok işareti görüntüsü
        
        # Animasyon ayarları
        self.animation_duration = 5000  # 5 saniye (milisaniye cinsinden)
        self.animation_start_time = 0  # Animasyonun başlama zamanı
        self.is_animating = False  # Animasyon durumu
        self.current_angle = 0  # Mevcut dönüş açısı
        self.rotation_count = 0  # Tamamlanan tur sayısı
        self.target_rotations = 3  # Hedef tur sayısı
        
        # Aynı isimde birden fazla taşa izin ver
        # Global olarak tanımla
        global allowMultiplePiece
        allowMultiplePiece = True
        
        # Uygulama ayarları
        self.settings = {
            "rotation_time": 5  # Varsayılan dönüş süresi (saniye)
        }
        
        # Modern temayı ayarla
        self.set_theme()
        
        # Kullanıcı arayüzünü oluştur
        self.setup_ui()
        
        # Dümen resmini hemen yükle
        self.preload_wheel_image()
        
    def set_theme(self):
        """
        Uygulama için modern ve tutarlı bir tema ayarlar.
        
        Butonlar, etiketler ve diğer arayüz elemanları için
        özel stiller tanımlar.
        """
        style = ttk.Style()
        style.theme_use('clam')  # Modern bir temel tema kullan
        
        # Çeşitli elemanlar için stiller yapılandır
        # Ana butonlar için stil
        style.configure("TButton", 
                       font=("Arial", 12),
                       padding=10,
                       background="#4CAF50",
                       foreground="white")
        
        # Ayarlar butonu için özel stil
        style.configure("Settings.TButton",
                       font=("Arial", 12),
                       padding=8,
                       background="#2196F3",
                       foreground="white")
        
        # Dümen çevirme butonu için dikkat çekici stil               
        style.configure("TurnWheel.TButton", 
                       font=("Arial", 14, "bold"),
                       padding=12,
                       background="#FF5722",
                       foreground="white")
        
        # Hover efektleri için stil haritaları
        # Normal butonlar için hover efekti               
        style.map("TButton", 
                 background=[("active", "#66BB6A")],
                 foreground=[("active", "white")])
        
        # Ayarlar butonu için hover efekti         
        style.map("Settings.TButton", 
                 background=[("active", "#42A5F5")],
                 foreground=[("active", "white")])
        
        # Dümen çevirme butonu için hover efekti         
        style.map("TurnWheel.TButton", 
                 background=[("active", "#FF7043")],
                 foreground=[("active", "white")])
        
    def setup_ui(self):
        """
        Kullanıcı arayüzünü oluşturur ve düzenler.
        
        Giriş alanları, butonlar, dümen ve sonuç bölümleri için
        gerekli tüm arayüz elemanlarını yerleştirir.
        """
        # Üst kısım için giriş çerçevesi
        input_frame = ttk.Frame(self.root, padding="10")
        input_frame.pack(fill=tk.X)
        
        # Ana içerik çerçevesi
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)
        
        # Kullanıcı adı girişi
        ttk.Label(input_frame, text="Lichess Kullanıcı Adı:").pack(side=tk.LEFT)
        self.username_entry = ttk.Entry(input_frame, width=30)
        self.username_entry.pack(side=tk.LEFT, padx=5)
        
        # Kullanıcı adı seçme butonu
        self.fetch_btn = ttk.Button(input_frame, text="Kullanıcı adını seç", command=self.set_username)
        self.fetch_btn.pack(side=tk.LEFT, padx=5)
        
        # Ayarlar butonu
        self.settings_btn = ttk.Button(
            input_frame, 
            text="⚙️ Ayarlar", 
            command=self.open_settings,
            style="Settings.TButton"
        )
        self.settings_btn.pack(side=tk.LEFT, padx=5)

        # Durum bilgisi için etiket
        self.status_var = tk.StringVar(value="Lichess kullanıcı adınızı girin ve 'Kullanıcı adını seç' butonuna tıklayın")
        status_label = ttk.Label(input_frame, textvariable=self.status_var)
        status_label.pack(side=tk.RIGHT, padx=5)
        
        # Dümen ve sonuç için merkezi bir konteyner
        wheel_container = ttk.Frame(main_frame)
        wheel_container.pack(expand=True, fill=tk.BOTH)
        
        # Dümen için tuval - merkezde konumlandır
        self.canvas = tk.Canvas(wheel_container, height=500, width=500, bg="white")
        self.canvas.pack(expand=True)
        
        # Dümeni göstermeden önce tuvalin düzgün boyutlandırılmasını bekle
        self.root.update_idletasks()
        
        # Sonuç gösterimi için etiket - dümenin hemen altında
        self.result_var = tk.StringVar()
        self.result_label = ttk.Label(wheel_container, textvariable=self.result_var, font=("Arial", 18, "bold"))
        self.result_label.pack(pady=10)
        
        # "Dümeni Çevir" butonu - dümen konteynerinin altında
        self.turn_wheel_btn = ttk.Button(
            wheel_container, 
            text="Dümeni Çevir", 
            command=self.turn_wheel,
            style="TurnWheel.TButton"
        )
        self.turn_wheel_btn.pack(pady=10)
        
        # Ok resmi yükleme
        try:
            # Ok görselinin dosya yolunu belirle
            arrow_path = os.path.join(os.path.dirname(sys.executable), "arrow.png")
            
            # Dosya yoksa basit bir ok görüntüsü oluştur
            if not os.path.exists(arrow_path):
                self.create_arrow_image()
                arrow_path = os.path.join(os.path.dirname(sys.executable), "arrow1.png")
            
            # Ok görüntüsünü yükle ve boyutlandır
            arrow_img = Image.open(arrow_path)
            arrow_img = arrow_img.resize((50, 60))  # İhtiyaca göre boyutlandır
            self.arrow_image = ImageTk.PhotoImage(arrow_img)
            
        except Exception as e:
            print(f"Ok resmi yüklenirken hata oluştu: {e}")
            self.arrow_image = None

    def create_arrow_image(self):
        """
        Eğer ok resmi yoksa basit bir ok resmi oluşturur ve kaydeder.
        
        Bu metod, uygulama ilk çalıştırıldığında ok görseli
        bulunamazsa otomatik olarak bir ok görüntüsü oluşturur.
        """
        from PIL import Image, ImageDraw
        
        # Şeffaf arka plana sahip yeni bir görüntü oluştur
        img = Image.new('RGBA', (100, 60), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        # Basit bir üçgen ok çiz
        draw.polygon([(0, 20), (0, 40), (80, 30)], fill=(255, 0, 0, 255))
        
        # Oluşturulan görüntüyü kaydet
        img_path = os.path.join(os.path.dirname(sys.executable), "arrow.png")
        img.save(img_path)

    def set_username(self):
        """
        Lichess oyun verilerini çekmek için kullanıcı adını ayarlar.
        
        Kullanıcının girdiği adı doğrular ve geçerli bir değer girildiyse
        kullanıcı adını uygulama için aktif hale getirir.
        """
        # Girilen kullanıcı adını al ve boşlukları temizle
        self.username = self.username_entry.get().strip()
        
        # Kullanıcı adı boşsa hata mesajı göster
        if not self.username:
            messagebox.showerror("Hata", "Lichess kullanıcı adınızı girin.")
            return
        
        # Kullanıcı adı başarıyla ayarlandı
        self.status_var.set(f"Dümen hazır. {self.username}")
        
    def turn_wheel(self):
        """
        Lichess'ten güncel oyun verilerini çeker ve dümeni çevirir.
        
        Kullanıcı adının ayarlanmış olup olmadığını ve animasyon 
        durumunu kontrol eder, ardından bir iş parçacığında veri 
        çekme işlemini başlatır.
        """
        # Kullanıcı adının ayarlanıp ayarlanmadığını kontrol et
        if not self.username:
            messagebox.showerror("Hata", "Dümeni çevirmek için Lichess kullanıcı adınızı girin.")
            return
        
        # Animasyon zaten çalışıyorsa işlemi engelle
        if self.is_animating:
            return
        
        # Kullanıcıya bilgi ver
        self.status_var.set(f"{self.username} için oyun verisi alınıyor...")
        
        # Kullanıcı arayüzünü dondurmamak için ayrı bir iş parçacığında veri çekme işlemini başlat
        threading.Thread(target=self.fetch_game_data, daemon=True).start()
    
    def fetch_game_data(self):
        """
        Lichess API'den kullanıcının güncel oyun verilerini çeker ve işler.
        
        Bu metod, belirtilen kullanıcı adına ait aktif satranç oyununu bulur,
        oyun sayfasından FEN pozisyonunu çıkarır ve analiz edilmek üzere
        process_fen metoduna gönderir.
        """
        try:
            # Kullanıcı bilgisi göster
            self.status_var.set(f"{self.username} için aktif oyun aranıyor...")
            
            # Lichess API URL'ini hazırla
            api_url = f"https://lichess.org/api/user/{self.username}/current-game"
            
            # API istekleri için gerekli başlık bilgileri
            headers = {
                'User-Agent': 'DumenDunyam/1.0 (Satranc tas secim ruleti uygulamasi)'
            }
            
            # API'den oyun verilerini çek, 10 saniye zaman aşımı ile
            self.status_var.set(f"{self.username} kullanıcısının aktif oyun verisi alınıyor...")
            api_response = requests.get(api_url, headers=headers, timeout=10)
            
            # Başarılı cevap kontrolü
            if api_response.status_code == 200:
                # PGN verisinden oyun ID'sini çıkar
                game_data = api_response.text
                game_id_match = re.search(r'\[GameId "([^"]+)"\]', game_data)
                
                # Oyun ID'si bulundu mu kontrolü
                if game_id_match:
                    # Oyun ID'sini kaydet
                    self.game_id = game_id_match.group(1)
                    
                    # Adım 2: Bu oyun için HTML sayfasını çek
                    game_url = f"https://lichess.org/{self.game_id}"
                    self.status_var.set(f"Oyun sayfası alınıyor: {self.game_id}")
                    
                    # Oyun sayfasını çek
                    html_response = requests.get(game_url, headers=headers, timeout=10)
                    
                    # Sayfa başarıyla alındıysa işle
                    if html_response.status_code == 200:
                        # Adım 3: HTML içeriğinden FEN verilerini çıkar ve işle
                        fen_text = self.extract_fen(html_response.text)
                        if fen_text:
                            # FEN pozisyonunu işle ve yasal hamleleri bul
                            self.process_fen(fen_text)
                        else:
                            # FEN bulunamadıysa hata mesajı göster
                            self.status_var.set("FEN verisi çıkarılamadı. Oyun henüz başlamamış olabilir.")
                    else:
                        # HTTP hata durumunda bilgi ver
                        self.status_var.set(f"Oyun sayfası alınırken hata oluştu (Kod: {html_response.status_code})")
                else:
                    # Aktif oyun bulunamadı bilgisi
                    self.status_var.set(f"{self.username} için aktif bir oyun bulunamadı. Lichess'te oyun başlatın ve tekrar deneyin.")
            else:
                # API hata durumunda bilgi ver
                self.status_var.set(f"Lichess API hatası: {api_response.status_code} - Lütfen kullanıcı adını kontrol edin.")
                
        except requests.exceptions.Timeout:
            # Zaman aşımı hatası için özel mesaj
            self.status_var.set("Lichess sunucusu yanıt vermedi. Lütfen internet bağlantınızı kontrol edin ve tekrar deneyin.")
        except requests.exceptions.ConnectionError:
            # Bağlantı hatası için özel mesaj
            self.status_var.set("Lichess'e bağlanılamadı. Lütfen internet bağlantınızı kontrol edin.")
        except Exception as e:
            # Genel hata durumunda bilgi ver (UI thread'inde güvenli şekilde göster)
            error_msg = str(e)
            self.root.after(0, lambda msg=error_msg: self.status_var.set(f"Hata oluştu: {msg}"))

    def extract_fen(self, html_content):
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # script tag ile sayfa içeriğini al
            script_tag = soup.select_one('script#page-init-data')

            if not script_tag:
                return None
            
            # son FEN pozisyonunu çıkar
            fen = script_tag.get_text().split('"fen":"')[-1].split('"')[0]
            print(fen)

            if not fen:
                return None

            return fen
            
        except Exception as e:
            self.status_var.set(f"FEN değeri işlenirken hata oldu: {str(e)}")
            return None

    def process_fen(self, fen):
        """
        FEN pozisyonunu işleyerek hareket edebilen taşları belirler.
        
        FEN (Forsyth-Edwards Notation), bir satranç pozisyonunu temsil eden standart
        bir gösterimdir. Bu metod, FEN'i işleyerek mevcut oyuncunun hangi taşları
        hareket ettirebileceğini analiz eder.
        
        Parametreler:
            fen (str): İşlenecek satranç pozisyonunun FEN gösterimi
        """
        try:
            # FEN ile yeni bir satranç tahtası oluştur
            self.board = chess.Board(fen)
            
            # Tüm yasal hamleleri al
            legal_moves = list(self.board.legal_moves)
            
            # Hareket edebilen benzersiz taşları tespit et
            piece_map = self.board.piece_map()
            movable_pieces = []

            # Taş tiplerini Türkçe isimlerle eşleştir
            piece_names = {
                chess.PAWN: "Piyon",
                chess.KNIGHT: "At",
                chess.BISHOP: "Fil",
                chess.ROOK: "Kale",
                chess.QUEEN: "Vezir",
                chess.KING: "Şah"
            }
            
            # Hangi oyuncunun sırası olduğunu belirle
            turn_color = self.board.turn
            print(f"Sıra rengi: {turn_color}")  # Debug bilgisi

            # Hareket edebilen tüm taşları bul
            for move in legal_moves:
                # Hamlenin başlangıç karesini al
                from_square = move.from_square
                
                # Karede bir taş olup olmadığını kontrol et
                if from_square in piece_map:
                    # Taş nesnesini al
                    piece = piece_map[from_square]
                    
                    # Taşın sırası gelen oyuncuya ait olup olmadığını kontrol et
                    if piece.color == turn_color:
                        # Taşın Türkçe adını al
                        piece_name = piece_names[piece.piece_type]
                        
                        # Eğer listede yoksa taş adını ekle
                        if piece_name not in movable_pieces:
                            movable_pieces.append(piece_name)
            
            # Hareket edebilen taşları sınıf değişkenine kaydet
            self.movable_pieces = movable_pieces
            
            # Sırayı Türkçe olarak belirle
            if turn_color:
                turn_color = "Beyaz"                
            else:
                turn_color = "Siyah"
            
            # Debug çıktıları - geliştirme aşamasında yararlı
            # print(f"Taşların rengi: {turn_color}")
            # print(f"Hareket edebilen taşlar: {movable_pieces}")
            
            # Eğer hareket edebilen taşlar varsa dümeni döndür
            if movable_pieces:
                # Kullanıcı arayüzünün güncellenmesi için küçük bir gecikme ekle
                self.root.after(100, lambda: self.spin_wheel(movable_pieces))
            else:
                self.result_var.set("Hareket edebilecek taş bulunamadı!")
        
        except Exception as e:
            self.status_var.set(f"FEN işlenirken hata oluştu: {str(e)}")

    def open_settings(self):
        """
        Ayarlar penceresini açar ve kullanıcı tercihlerini yapılandırır.
        
        Bu metod, dümen dönüş hızı gibi uygulama ayarlarını değiştirmek için
        kullanıcıya basit ve sezgisel bir arayüz sunar. Ayarlar, kullanıcı
        tarafından kaydedildikten sonra anında uygulanır.
        """
        # Yeni bir üst düzey pencere oluştur
        settings_dialog = tk.Toplevel(self.root)
        settings_dialog.title("Ayarlar")
        settings_dialog.geometry("400x300")
        settings_dialog.transient(self.root)  # İletişim kutusunu modal yap
        settings_dialog.grab_set()  # Odağı bu pencereye kilitle
        
        # Pencereyi ana pencerenin ortasına yerleştir
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (400 // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (300 // 2)
        settings_dialog.geometry(f"+{x}+{y}")
        
        # İçerik için dolgu ile bir çerçeve oluştur
        frame = ttk.Frame(settings_dialog, padding="20")
        frame.pack(expand=True, fill=tk.BOTH)
        
        # Dönüş süresi için etiket
        ttk.Label(frame, text="Dümen Dönüş Süresi (saniye):", font=("Arial", 12)).pack(pady=10)
        
        # Dönüş süresini ayarlamak için kaydırıcı
        rotation_scale = ttk.Scale(
            frame, 
            from_=1,  # Minimum değer: 1 saniye
            to=10,    # Maksimum değer: 10 saniye
            orient=tk.HORIZONTAL, 
            length=300,
            value=self.settings["rotation_time"]  # Mevcut değeri göster
        )
        rotation_scale.pack(pady=10)
        
        # Seçilen değeri gösteren etiket
        value_var = tk.StringVar(value=f"{self.settings['rotation_time']} saniye")
        value_label = ttk.Label(frame, textvariable=value_var, font=("Arial", 14, "bold"))
        value_label.pack(pady=10)
        
        # Kaydırıcı hareket ettiğinde değer etiketini güncelle
        def update_value(event):
            value = round(rotation_scale.get())  # Tam sayıya yuvarla
            value_var.set(f"{value} saniye")
        
        rotation_scale.bind("<Motion>", update_value)
        
        # Ayarları kaydetme fonksiyonu
        def save_settings():
            # Yuvarlanan değeri ayarlara kaydet
            self.settings["rotation_time"] = round(rotation_scale.get())
            
            # Yeni değeri animasyon süresine uygula (ms cinsinden)
            self.animation_duration = self.settings["rotation_time"] * 1000
            
            # Ayarlar penceresini kapat
            settings_dialog.destroy()
        
        # Kaydet butonu
        ttk.Button(
            frame, 
            text="Kaydet", 
            command=save_settings,
            style="TButton"
        ).pack(pady=20)

    def preload_wheel_image(self):
        """
        Dümen görüntüsünü yükler ve animasyon için hazırlar.
        
        Bu metod, dümen görselini uygulamanın bulunduğu dizinden yükler.
        Eğer görsel bulunamazsa, varsayılan bir dümen görüntüsü oluşturur.
        Yüklenen görsel, performans için optimal boyuta getirilir ve
        önbelleğe alınır.
        """
        try:
            # exeninin bulunduğu dizinden dümen resmini yükle
            wheel_path = os.path.join(os.path.dirname(sys.executable), "dumen.png")            
            
            # Dosyanın var olup olmadığını kontrol et
            if not os.path.exists(wheel_path):
                # Görsel yoksa varsayılan bir dümen oluştur
                # self.create_default_wheel()
                # wheel_path = os.path.join(os.path.dirname(__file__), "dumen.png")
                FileNotFoundError("Dümen resmi bulunamadı.")
            
            # Görseli yükle
            original_image = Image.open(wheel_path)

            # Daha iyi performans için sabit bir boyut belirle
            wheel_size = 300
            
            # Görseli belirlenen boyuta yeniden boyutlandır
            resized_image = original_image.resize((wheel_size, wheel_size))
            
            # Orijinal ve boyutlandırılmış görselleri sakla
            self.wheel_image_original = resized_image
            self.wheel_image = ImageTk.PhotoImage(resized_image)
            
            # Kullanıcı arayüzünün güncellenmesine izin ver
            self.root.update_idletasks()
            
            # Dümeni hemen göster
            self.display_initial_wheel()
            
            # İşlemin başarılı olduğunu kullanıcıya bildir
            self.status_var.set("Dümen resmi yüklendi. Çevirmeye hazır.")
            
        except Exception as e:
            # Hata durumunda kullanıcıya bilgi ver
            error_msg = f"Dümen resmi yüklenirken hata oluştu: {str(e)}"
            self.status_var.set(error_msg)
    
    def display_initial_wheel(self):
        """
        Başlangıç dümen görselini tuvalde gösterir.
        
        Bu metod, dümen görselini ve ok işaretini tuval üzerinde
        uygun konumlarda gösterir. Tuval boyutlarını kontrol eder
        ve görsel elemanları dinamik olarak ortalayarak yerleştirir.
        """
        # Önceki çizimleri temizle
        self.canvas.delete("all")
        
        # Tuval boyutlarını al ve geçerli olduklarından emin ol
        self.root.update_idletasks()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Eğer tuval henüz düzgün boyutlandırılmamışsa varsayılan değerleri kullan
        if canvas_width < 100:  
            canvas_width = 600
        if canvas_height < 100:
            canvas_height = 600
        
        # Merkez koordinatları hesapla
        center_x = canvas_width // 2
        center_y = canvas_height // 2
        
        # Dümeni merkeze yerleştir
        if self.wheel_image:
            self.canvas.create_image(center_x, center_y, image=self.wheel_image, tags=("wheel",))
            
            # Ok işaretini yerleştir
            if self.arrow_image:
                # Eğer ok görseli varsa, onu kullan
                arrow_x = center_x + (self.wheel_image.width() // 2) + 100
                arrow_y = center_y
                self.canvas.create_image(arrow_x, arrow_y, image=self.arrow_image, tags=("arrow",))
            else:
                # Görsel yoksa basit bir ok şekli çiz
                arrow_x = center_x + (self.wheel_image.width() // 2) + 30
                arrow_y = center_y
                self.canvas.create_polygon(
                    arrow_x, arrow_y-15, 
                    arrow_x+30, arrow_y, 
                    arrow_x, arrow_y+15, 
                    fill="red",  # Kırmızı dolgu
                    outline="black",  # Siyah çerçeve
                    tags=("arrow",)
                )

    def spin_wheel(self, pieces):
        """
        Dümen çevirme animasyonunu başlatır.
        
        Bu metod, dümen çarkının dönüş animasyonunu hazırlar ve başlatır.
        Taşları dümenin etrafına yerleştirir ve kullanıcının seçeceği
        taşı belirlemek için animasyon sürecini yönetir.
        
        Parametreler:
            pieces (list): Dümen etrafına yerleştirilecek taş isimleri listesi
        """
        # Zaten animasyon çalışıyorsa işlemi engelle
        if self.is_animating:
            return
            
        # Önceki sonucu temizle
        self.result_var.set("")
        
        # Tuvali temizle
        self.canvas.delete("all")
        
        # Tuval boyutlarını ve merkez koordinatlarını hesapla
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        center_x = canvas_width // 2
        center_y = canvas_height // 2
        
        # Dümen görselini merkeze yerleştir
        wheel_id = self.canvas.create_image(center_x, center_y, image=self.wheel_image, tags=("wheel",))
        
        # Ok işaretini yerleştir
        if self.arrow_image:
            # Eğer ok görseli varsa, onu kullan
            arrow_x = center_x + (self.wheel_image.width() // 2) + 100
            arrow_y = center_y
            self.canvas.create_image(arrow_x, arrow_y, image=self.arrow_image, tags=("arrow",))
        else:
            # Görsel yoksa basit bir ok şekli çiz
            arrow_x = center_x + (self.wheel_image.width() // 2) + 30
            arrow_y = center_y
            self.canvas.create_polygon(
                arrow_x, arrow_y-15, 
                arrow_x+30, arrow_y, 
                arrow_x, arrow_y+15, 
                fill="red",  # Kırmızı dolgu
                outline="black",  # Siyah çerçeve
                tags=("arrow",)
            )
        
        # Taşları dümenin etrafına yerleştir
        self.position_pieces_around_wheel(pieces, center_x, center_y)
        
        # Animasyon değişkenlerini başlat
        self.is_animating = True
        self.animation_start_time = time.time() * 1000  # Başlangıç zamanı (ms)
        self.current_angle = 0
        self.rotation_count = 0
        
        # Animasyonu başlat
        self.animate_wheel()

    def position_pieces_around_wheel(self, pieces, center_x, center_y):
        """
        Taş isimlerini dümenin etrafına düzenli bir şekilde yerleştirir.
        
        Bu metod, oynanabilir taş isimlerini dümen çarkının etrafında eşit aralıklarla
        konumlandırır. Her taşın adını, dümenin dönüşüne uygun şekilde yerleştirir ve
        animasyon sırasında pozisyonlarını güncellemek için gerekli bilgileri saklar.
        
        Parametreler:
            pieces (list): Yerleştirilecek taş isimlerinin listesi
            center_x (int): Dümenin merkez X koordinatı
            center_y (int): Dümenin merkez Y koordinatı
        """
        # Eğer taş listesi boşsa işlemi sonlandır
        if not pieces:
            return
            
        # Dümen çarkının yarıçapını hesapla
        wheel_radius = self.wheel_image.width() // 2
        
        # Taşların yerleştirileceği açıları hesapla
        num_pieces = len(pieces)
        angle_step = 360 / num_pieces  # Taşlar arasındaki açı farkı
        
        # Animasyon için taş konumlarını sakla
        self.piece_positions = []
        
        # Her bir taş için metin öğeleri oluştur
        for i, piece in enumerate(pieces):
            # Taşın açı değerini hesapla
            angle = i * angle_step
            radians = math.radians(angle)
            
            # Metni dümenin dışında konumlandır
            text_radius = wheel_radius + 40  # Dümen dışında 40 piksel boşluk bırak

            # Polar koordinatları kartezyen koordinatlara dönüştür
            x = center_x + int(text_radius * math.cos(radians))
            y = center_y + int(text_radius * math.sin(radians))
            
            # Benzersiz bir etiketle metin oluştur
            text_id = self.canvas.create_text(
                x, y, 
                text=piece,  # Taşın adı
                font=("Arial", 16, "bold"),  # Kalın yazı tipi
                fill="black",  # Siyah renk
                angle=-angle,  # Okunaklı kalması için metni ters döndür
                tags=(f"piece_{i}", "piece")  # Tanımlama etiketleri
            )
            
            # Animasyon sırasında kullanmak için konum bilgilerini sakla
            self.piece_positions.append({
                "id": text_id,      # Tuval üzerindeki metin öğesinin ID'si
                "angle": angle,     # Taşın başlangıç açısı
                "radius": text_radius  # Merkeze olan uzaklığı
            })

    def animate_wheel(self):
        """
        Dümen çarkının animasyonunu gelişmiş yumuşatma (easing) efektiyle yönetir.
        
        Bu metot, dümen çarkının dönüş animasyonunu kontrol eder, gerçekçi bir
        fizik hissi vermek için başlangıçta hızlı, sona doğru yavaşlayan bir 
        hareket sağlar. Animasyon süresi, ayarlardaki değere göre belirlenir.
        """
        # Eğer animasyon aktif değilse metoddan çık
        if not self.is_animating:
            return
            
        # Geçen süreyi hesapla (milisaniye cinsinden)
        current_time = time.time() * 1000
        elapsed = current_time - self.animation_start_time
        
        # Animasyon süresini aştıysak, animasyonu sonlandır
        if elapsed >= self.animation_duration:
            self.finish_animation()
            return

        # İlerleme oranını hesapla (0-1 arası)
        progress = elapsed / self.animation_duration
        
        # Geliştirilmiş yumuşatma faktörünü hesapla
        # Animasyonun sonuna doğru daha dramatik bir yavaşlama efekti için
        # easeOutCubic ve easeOutQuint kombinasyonu kullanılıyor
        if progress < 0.7:  # Animasyonun ilk %70'i - daha sabit hız
            eased_progress = 0.7 * progress / 0.7
        else:  # Son %30 - dramatik yavaşlama
            p = (progress - 0.7) / 0.3  # Bu segment için 0-1 aralığına normalize et
            # Daha belirgin yavaşlama eğrisi
            eased_progress = 0.7 + 0.3 * (1 - (1 - p) ** 5)
        
        # Tam olarak hedef dönüş sayısı artı rastgele bir bitiş pozisyonu sağla
        total_rotations = self.target_rotations + (random.random() * 0.8 + 0.1)  # Rastgele final pozisyonu
        target_angle = total_rotations * 360 * eased_progress
        
        # Tekerleğin dönüşünü hesaplanan açıya göre güncelle
        self.rotate_wheel_to_angle(target_angle)
        
        # Tam bir tur tamamlandığında kontrol et
        current_rotation = int(target_angle / 360)
        if current_rotation > self.rotation_count:
            self.rotation_count = current_rotation
            # Ara sonuçlar gösterilmek istenirse buraya kod eklenebilir
            # Şu an için bu özellik devre dışı
            
        # Optimum görüntü akışı için sonraki kareyi zamanla (16ms = yaklaşık 60 FPS)
        self.root.after(16, self.animate_wheel)  # Yaklaşık saniyede 60 kare

    def rotate_wheel_to_angle(self, angle):
        """
        Dümen çarkını belirtilen açıya döndürür.
        
        Bu metod, performans optimizasyonu için önbellek mekanizması kullanır.
        Her 10 derecelik açı için döndürülmüş resimler önbelleğe alınarak
        tekrar hesaplama maliyetinden kaçınılır.
        
        Parametreler:
            angle (float): Dümenin döndürüleceği açı değeri (derece cinsinden)
        """
        # Performans optimizasyonu için belirli aralıklarla önbelleğe alma
        cache_key = int(angle / 10) * 10  # Her 10 derecede bir önbelleğe al
        
        if cache_key in self.wheel_images_cache:
            # Eğer bu açı için daha önce hesaplanmış bir görüntü varsa kullan
            rotated_image = self.wheel_images_cache[cache_key]
        else:
            # Orijinal görüntüyü istenilen açıya döndür
            # Saat yönünde dönüş için negatif açı kullanılır
            rotated_img = self.wheel_image_original.rotate(-angle)
            rotated_image = ImageTk.PhotoImage(rotated_img)
            
            # Bellek yönetimini optimize etmek için sadece 10'un katı olan açıları önbelleğe al
            if angle % 10 < 0.1:
                self.wheel_images_cache[cache_key] = rotated_image
        
        # Dümen görselini güncelle
        self.canvas.itemconfig("wheel", image=rotated_image)
        
        # Çöp toplayıcının görüntüyü silmemesi için referansı sakla
        self.wheel_image = rotated_image
        
        # Taşların konumlarını yeni açıya göre güncelle
        self.update_piece_positions(angle)

    def update_piece_positions(self, angle):
        """
        Dümen çarkının dönüşüne bağlı olarak taş isimlerinin pozisyonlarını günceller.
        
        Bu metod, dönmekte olan dümen çarkı etrafındaki taş isimlerinin konumlarını 
        ve açılarını dinamik olarak hesaplar ve günceller. Böylece taş isimleri dümenin
        dönüş hareketiyle uyumlu şekilde hareket eder.
        
        Parametreler:
            angle (float): Dümenin mevcut dönüş açısı (derece cinsinden)
        """
        # Tuval boyutlarını al ve merkez koordinatlarını hesapla
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        center_x = canvas_width // 2
        center_y = canvas_height // 2
        
        # Tüm taş konumları için yeni pozisyonları hesapla ve uygula
        for pos in self.piece_positions:
            # Taşın yeni açısını hesapla (başlangıç açısı + dümen dönüş açısı)
            new_angle = pos["angle"] + angle
            # Açıyı radyana çevir (trigonometrik hesaplamalar için)
            radians = math.radians(new_angle)
            
            # Taşın yeni x ve y koordinatlarını hesapla (polar koordinattan kartezyen koordinata dönüşüm)
            x = center_x + int(pos["radius"] * math.cos(radians))
            y = center_y + int(pos["radius"] * math.sin(radians))
            
            # Taş metninin pozisyonunu güncelle
            self.canvas.coords(pos["id"], x, y)
            # Metnin dönüş açısını güncelle (okunabilirliği korumak için ters döndür)
            self.canvas.itemconfig(pos["id"], angle=-new_angle)  # Metni ters yönde döndür

    def finish_animation(self):
        """
        Dümen animasyonunu sonlandırır ve sonucu belirler.
        
        Bu metot animasyonun bitiminde çalışır, dümeni durdurur ve
        ok işaretinin gösterdiği taşı belirleyerek kullanıcıya sonucu gösterir.
        Sonuç, görsel olarak vurgulanır ve kullanıcıya hangi taşla hamle yapması
        gerektiği bildirilir.
        """
        
        self.is_animating = False  # Animasyon durumunu kapat
        # Ok işaretinin gösterdiği taşı bul
        result = self.determine_selected_piece()

        
        if result:
            # Hamle sırasının hangi renkte olduğunu belirle
            turn_color = "Beyaz" if self.board.turn else "Siyah"
            
            # Sonucu görüntüle
            result_text = f"{turn_color} TAŞ: {result.upper()}"
            self.result_var.set(result_text)
            
            # Sonucu görsel olarak vurgula
            self.result_label.configure(foreground="#FF5722")  # Turuncu renk ile vurgula
        else:
            # Sonuç bulunamazsa hata mesajı göster
            self.result_var.set("Sonuç belirlenemedi!")

    def determine_selected_piece(self):
        """
        Ok işaretinin gösterdiği taşı belirler.
        
        Bu metot, ok işaretinin konumunu alır ve dümende bulunan
        taş isimleri arasından oka en yakın olanı tespit eder. 
        Uzaklık hesaplaması için Öklid mesafesi kullanılır.
        
        Dönüş değeri:
            str: Seçilen taşın adı, tespit edilemezse None
        """
        try:
            # Ok işaretinin konumunu al
            arrow_item = self.canvas.find_withtag("arrow")
            if not arrow_item:
                return None
                
            arrow_x, arrow_y = self.canvas.coords(arrow_item[0])
            
            # Oka en yakın taşı bul
            nearest_piece = None
            min_distance = float('inf')  # Başlangıçta sonsuz mesafe
            
            # Tüm taş konumlarını kontrol et
            for pos in self.piece_positions:
                piece_id = pos["id"]
                piece_x, piece_y = self.canvas.coords(piece_id)
                
                # Öklid mesafesini hesapla
                distance = math.sqrt((piece_x - arrow_x) ** 2 + (piece_y - arrow_y) ** 2)
                
                # Eğer daha yakınsa güncelle
                if distance < min_distance:
                    min_distance = distance
                    nearest_piece = piece_id
            
            # Eğer bir taş bulunduysa adını döndür
            if nearest_piece:
                piece_text = self.canvas.itemcget(nearest_piece, "text")
                return piece_text
        
        except Exception as e:
            # Hata durumunda konsola bilgi ver
            print(f"Seçilen taş belirlenirken hata oluştu: {e}")
        
        return None

def main():
    root = tk.Tk()
    app = DumenApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
