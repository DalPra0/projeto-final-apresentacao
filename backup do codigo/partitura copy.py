import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import os
import json
import fitz
import shutil
import threading
import time
from PIL import Image, ImageTk
import pygame

CONFIG_FILE = "config.json"

INSTRUMENTS = ["guitarra", "baixo", "violao", "violino", "piano"]

class PDFViewer(tk.Toplevel):
    def __init__(self, master, pdf_path):
        super().__init__(master)
        self.title("Visualizador de PDF")
        self.pdf_document = fitz.open(pdf_path)
        self.current_page = 0

        self.canvas = tk.Canvas(self)
        self.canvas.pack(fill=tk.BOTH, expand=1)

        self.load_page(self.current_page)

        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.prev_button = ttk.Button(btn_frame, text="Anterior", command=self.prev_page)
        self.prev_button.pack(side=tk.LEFT)

        self.next_button = ttk.Button(btn_frame, text="Próxima", command=self.next_page)
        self.next_button.pack(side=tk.LEFT)

        self.exit_button = ttk.Button(btn_frame, text="Sair", command=self.destroy)
        self.exit_button.pack(side=tk.RIGHT)

    def load_page(self, page_num):
        if 0 <= page_num < self.pdf_document.page_count:
            page = self.pdf_document.load_page(page_num)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            self.photo = ImageTk.PhotoImage(img)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

    def next_page(self):
        if self.current_page < self.pdf_document.page_count - 1:
            self.current_page += 1
            self.load_page(self.current_page)

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.load_page(self.current_page)

class Metronome(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Metrônomo")
        self.bpm = tk.IntVar(value=120)
        self.running = False

        # Initialize pygame mixer
        pygame.mixer.init()

        tk.Label(self, text="BPM:").pack(pady=10)
        self.bpm_entry = tk.Entry(self, textvariable=self.bpm)
        self.bpm_entry.pack(pady=10)

        self.start_button = tk.Button(self, text="Iniciar", command=self.start)
        self.start_button.pack(pady=10)

        self.stop_button = tk.Button(self, text="Parar", command=self.stop)
        self.stop_button.pack(pady=10)

    def start(self):
        if not self.running:
            self.running = True
            self.metronome_thread = threading.Thread(target=self.run_metronome)
            self.metronome_thread.start()

    def stop(self):
        self.running = False
        pygame.mixer.stop()

    def run_metronome(self):
        while self.running:
            print("Tick")
            tick_sound = pygame.mixer.Sound("sounds/tick.wav")
            tick_sound.play()
            time.sleep(60 / self.bpm.get())


class InstrumentSelector(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Selecione seus instrumentos")

        self.selected_instruments = []

        tk.Label(self, text="Selecione os instrumentos que você toca:").pack(pady=10)
        
        self.instrument_vars = {instrument: tk.BooleanVar() for instrument in INSTRUMENTS}

        for instrument, var in self.instrument_vars.items():
            ttk.Checkbutton(self, text=instrument.capitalize(), variable=var).pack(anchor=tk.W)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Confirmar", command=self.confirm).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT)

    def confirm(self):
        self.selected_instruments = [instrument for instrument, var in self.instrument_vars.items() if var.get()]
        if self.selected_instruments:
            self.master.save_instruments(self.selected_instruments)
            self.master.show_main_screen()
            self.destroy()
        else:
            messagebox.showerror("Erro", "Selecione pelo menos um instrumento.")

class Settings(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Configurações")

        self.selected_instruments = master.user_instruments[:]

        tk.Label(self, text="Selecione os instrumentos que você toca:").pack(pady=10)

        self.instrument_vars = {instrument: tk.BooleanVar(value=(instrument in self.selected_instruments)) for instrument in INSTRUMENTS}

        for instrument, var in self.instrument_vars.items():
            ttk.Checkbutton(self, text=instrument.capitalize(), variable=var).pack(anchor=tk.W)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Salvar", command=self.save).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="Adicionar mais partituras", command=self.add_pdf).pack(side=tk.LEFT, pady=10)

    def save(self):
        self.selected_instruments = [instrument for instrument, var in self.instrument_vars.items() if var.get()]
        if self.selected_instruments:
            self.master.save_instruments(self.selected_instruments)
            self.destroy()
        else:
            messagebox.showerror("Erro", "Selecione pelo menos um instrumento.")

    def add_pdf(self):
        pdf_path = filedialog.askopenfilename(title="Selecione a partitura", filetypes=[("Arquivos PDF", "*.pdf")])
        if pdf_path:
            instrument = tk.simpledialog.askstring("Instrumento", "Para qual instrumento é essa partitura?", initialvalue=self.selected_instruments[0] if self.selected_instruments else "")
            if instrument and instrument in INSTRUMENTS:
                instrument_dir = os.path.join("partituras", instrument)
                if not os.path.exists(instrument_dir):
                    os.makedirs(instrument_dir)
                shutil.copy(pdf_path, instrument_dir)
                messagebox.showinfo("Sucesso", "Partitura adicionada com sucesso!")
            else:
                messagebox.showerror("Erro", "Instrumento inválido ou não selecionado.")

class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Leitor de PDF de Partituras")

        self.load_user_settings()
        self.create_widgets()

        if not self.user_instruments:
            self.show_instrument_selector()
        else:
            self.show_main_screen()

    def create_widgets(self):
        self.main_frame = tk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=1)

    def show_instrument_selector(self):
        self.withdraw()
        InstrumentSelector(self)

    def show_main_screen(self):
        self.main_frame.pack_forget()
        self.main_frame = tk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=1)

        tk.Label(self.main_frame, text="Instrumentos que você toca:").pack(pady=10)

        for instrument in self.user_instruments:
            btn = ttk.Button(self.main_frame, text=instrument.capitalize(), command=lambda i=instrument: self.show_pdfs(i))
            btn.pack(fill=tk.X, padx=20, pady=5)

        ttk.Button(self.main_frame, text="Configurações", command=self.show_settings).pack(pady=10)
        ttk.Button(self.main_frame, text="Metrônomo", command=self.show_metronome).pack(pady=10)
        ttk.Button(self.main_frame, text="Buscar Partitura", command=self.search_pdf).pack(pady=10)
        ## ttk.Button(self.main_frame, text="Modo de Prática", command=self.practice_mode).pack(pady=10)
        ## ttk.Button(self.main_frame, text="Banco de Dados", command=self.fetch_from_database).pack(pady=10)
        ## ttk.Button(self.main_frame, text="Visualizar Tablatura", command=self.show_tab).pack(pady=10)

    def show_pdfs(self, instrument):
        pdf_dir = os.path.join("partituras", instrument)
        if os.path.exists(pdf_dir):
            pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
            if pdf_files:
                self.show_pdf_selection(instrument, pdf_files)
            else:
                messagebox.showerror("Erro", "Nenhuma partitura encontrada para este instrumento.")
        else:
            messagebox.showerror("Erro", "Pasta de partituras não encontrada.")

    def show_pdf_selection(self, instrument, pdf_files):
        selection_window = tk.Toplevel(self)
        selection_window.title(f"Selecione uma partitura para {instrument.capitalize()}")

        tk.Label(selection_window, text="Selecione a partitura:").pack(pady=10)

        listbox = tk.Listbox(selection_window)
        for pdf in pdf_files:
            listbox.insert(tk.END, pdf)
        listbox.pack(fill=tk.BOTH, expand=1, pady=10, padx=10)

        def open_selected_pdf():
            selected = listbox.curselection()
            if selected:
                pdf_path = os.path.join("partituras", instrument, pdf_files[selected[0]])
                PDFViewer(self, pdf_path)
                selection_window.destroy()
            else:
                messagebox.showerror("Erro", "Nenhuma partitura selecionada.")

        btn_frame = tk.Frame(selection_window)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Abrir", command=open_selected_pdf).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Cancelar", command=selection_window.destroy).pack(side=tk.RIGHT)

    def show_settings(self):
        Settings(self)

    def load_user_settings(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as file:
                settings = json.load(file)
                self.user_instruments = settings.get("instruments", [])
        else:
            self.user_instruments = []

    def save_instruments(self, instruments):
        self.user_instruments = instruments
        self.save_user_settings()

    def save_user_settings(self):
        settings = {
            "instruments": self.user_instruments
        }
        with open(CONFIG_FILE, "w") as file:
            json.dump(settings, file)

    def show_metronome(self):
        Metronome(self)

    def search_pdf(self):
        search_term = simpledialog.askstring("Buscar Partitura", "Digite o nome da partitura:")
        if search_term:
            results = []
            for instrument in self.user_instruments:
                pdf_dir = os.path.join("partituras", instrument)
                if os.path.exists(pdf_dir):
                    pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf') and search_term.lower() in f.lower()]
                    for pdf in pdf_files:
                        results.append((instrument, pdf))
            if results:
                self.show_search_results(results)
            else:
                messagebox.showinfo("Busca", "Nenhuma partitura encontrada.")

    def fetch_from_database(self):
        # Esta função deve conectar a um banco de dados real em um cenário real
        available_pdfs = [("violino", "Beethoven_Sonata.pdf"), ("piano", "Chopin_Nocturne.pdf")]
        self.show_search_results(available_pdfs)

    def show_search_results(self, results):
        result_window = tk.Toplevel(self)
        result_window.title("Resultados da Busca")

        tk.Label(result_window, text="Resultados da Busca:").pack(pady=10)

        listbox = tk.Listbox(result_window)
        for instrument, pdf in results:
            listbox.insert(tk.END, f"{instrument.capitalize()}: {pdf}")
        listbox.pack(fill=tk.BOTH, expand=1, pady=10, padx=10)

        def open_selected_result():
            selected = listbox.curselection()
            if selected:
                instrument, pdf = results[selected[0]]
                pdf_path = os.path.join("partituras", instrument, pdf)
                PDFViewer(self, pdf_path)
                result_window.destroy()
            else:
                messagebox.showerror("Erro", "Nenhuma partitura selecionada.")

        btn_frame = tk.Frame(result_window)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Abrir", command=open_selected_result).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Cancelar", command=result_window.destroy).pack(side=tk.RIGHT)

    def practice_mode(self):
        instrument = simpledialog.askstring("Modo de Prática", "Digite o nome do instrumento:")
        if instrument:
            audio_path = filedialog.askopenfilename(title="Selecione a gravação de prática", filetypes=[("Arquivos de Áudio", "*.mp3 *.wav")])
            if audio_path:
                self.current_instrument = instrument
                self.show_pdfs(instrument)
                pygame.mixer.init()
                pygame.mixer.music.load(audio_path)
                pygame.mixer.music.play()

    def show_tab(self):
        instrument = simpledialog.askstring("Visualizar Tablatura", "Digite o nome do instrumento:")
        if instrument:
            tab_dir = os.path.join("tablaturas", instrument)
            if os.path.exists(tab_dir):
                tab_files = [f for f in os.listdir(tab_dir) if f.endswith('.txt')]
                if tab_files:
                    self.show_tab_selection(instrument, tab_files)
                else:
                    messagebox.showerror("Erro", "Nenhuma tablatura encontrada para este instrumento.")
            else:
                messagebox.showerror("Erro", "Pasta de tablaturas não encontrada.")
    
    def show_tab_selection(self, instrument, tab_files):
        selection_window = tk.Toplevel(self)
        selection_window.title(f"Selecione uma tablatura para {instrument.capitalize()}")

        tk.Label(selection_window, text="Selecione a tablatura:").pack(pady=10)

        listbox = tk.Listbox(selection_window)
        for tab in tab_files:
            listbox.insert(tk.END, tab)
        listbox.pack(fill=tk.BOTH, expand=1, pady=10, padx=10)

        def open_selected_tab():
            selected = listbox.curselection()
            if selected:
                tab_path = os.path.join("tablaturas", instrument, tab_files[selected[0]])
                with open(tab_path, 'r') as file:
                    tab_content = file.read()
                tab_viewer = tk.Toplevel(self)
                tab_viewer.title(f"Tablatura: {tab_files[selected[0]]}")
                text_widget = tk.Text(tab_viewer)
                text_widget.insert(tk.END, tab_content)
                text_widget.pack(fill=tk.BOTH, expand=1)
                selection_window.destroy()
            else:
                messagebox.showerror("Erro", "Nenhuma tablatura selecionada.")

        btn_frame = tk.Frame(selection_window)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Abrir", command=open_selected_tab).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Cancelar", command=selection_window.destroy).pack(side=tk.RIGHT)

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()