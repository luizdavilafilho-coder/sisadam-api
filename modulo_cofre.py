import customtkinter as ctk
import os
import pathlib
from datetime import datetime
from tkinter import messagebox

class Cofre(ctk.CTkFrame):
    def __init__(self, master, fg_color="transparent", nivel="ADMIN", **kwargs):
        super().__init__(master, fg_color=fg_color, **kwargs)
        
        self.nivel = nivel.strip().upper()
        self.pasta_base = pathlib.Path.home() / "Documents" / "SISADAM"
        
        # A MÁGICA ACONTECE AQUI: Adicionada a rota para a pasta do Backup do BD
        self.pastas_alvo = {
            "Word": self.pasta_base / "Arquivos_Word",
            "Excel": self.pasta_base / "Arquivos_Excel",
            "PDF": self.pasta_base / "Arquivos_PDF",
            "Backup BD": self.pasta_base / "Cofre_Backup" 
        }
        
        # Garante que as pastas existam
        for pasta in self.pastas_alvo.values():
            pasta.mkdir(parents=True, exist_ok=True)
            
        self.montar_interface()
        self.carregar_arquivos("Todos")

    def montar_interface(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Cabeçalho e Filtros ---
        f_top = ctk.CTkFrame(self, fg_color="transparent")
        f_top.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        titulo = "COFRE DE AUDITORIA / DOCUMENTOS"
        ctk.CTkLabel(f_top, text=titulo, font=("Arial", 24, "bold"), text_color="#F57C00").pack(side="left")
        
        self.filtro_var = ctk.StringVar(value="Todos")
        # Adicionado "Backup BD" à lista de filtros na tela
        filtros = ["Todos", "Word", "Excel", "PDF", "Backup BD"]
        
        for f in filtros:
            ctk.CTkRadioButton(f_top, text=f, variable=self.filtro_var, value=f, 
                               command=lambda: self.carregar_arquivos(self.filtro_var.get())).pack(side="right", padx=10)
        
        ctk.CTkLabel(f_top, text="Filtrar por:", text_color="white").pack(side="right", padx=10)

        # --- Área de Listagem (Scrollable) ---
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#121212")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.scroll_frame.grid_columnconfigure(1, weight=1)

    def carregar_arquivos(self, filtro):
        # Limpa a listagem anterior
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            
        # Cabeçalhos com texto BRANCO
        headers = ["Tipo", "Nome do Arquivo", "Data de Modificação", "Ações"]
        for col, texto in enumerate(headers):
            ctk.CTkLabel(self.scroll_frame, text=texto, font=("Arial", 14, "bold"), text_color="white").grid(row=0, column=col, padx=10, pady=(10, 20), sticky="w")

        linha_atual = 1
        arquivos_encontrados = False

        for tipo, caminho_pasta in self.pastas_alvo.items():
            if filtro != "Todos" and filtro != tipo:
                continue
                
            if caminho_pasta.exists():
                for arquivo in caminho_pasta.iterdir():
                    if arquivo.is_file():
                        arquivos_encontrados = True
                        self.criar_linha_arquivo(arquivo, tipo, linha_atual)
                        linha_atual += 1

        if not arquivos_encontrados:
            ctk.CTkLabel(self.scroll_frame, text="Nenhum documento encontrado nas pastas do Cofre.", 
                         font=("Arial", 14, "italic"), text_color="#888").grid(row=1, column=0, columnspan=4, pady=30)

    def criar_linha_arquivo(self, arquivo_path, tipo, linha):
        # Cores vibrantes para os selos de tipo de arquivo (Laranja adicionado para o Backup)
        cores_tipo = {"Word": "#2980b9", "Excel": "#27ae60", "PDF": "#c0392b", "Backup BD": "#F57C00"}
        
        # Selo do Tipo
        ctk.CTkLabel(self.scroll_frame, text=f" {tipo} ", fg_color=cores_tipo.get(tipo, "#555"), 
                     corner_radius=5, text_color="white", font=("Arial", 11, "bold")).grid(row=linha, column=0, padx=10, pady=5, sticky="w")
        
        # Nome do Arquivo 
        ctk.CTkLabel(self.scroll_frame, text=arquivo_path.name, font=("Arial", 12), text_color="white").grid(row=linha, column=1, padx=10, pady=5, sticky="w")
        
        # Data de Modificação 
        data_mod = datetime.fromtimestamp(arquivo_path.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
        ctk.CTkLabel(self.scroll_frame, text=data_mod, font=("Arial", 12), text_color="white").grid(row=linha, column=2, padx=10, pady=5, sticky="w")
        
        # Frame de Ações
        f_botoes = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        f_botoes.grid(row=linha, column=3, padx=10, pady=5, sticky="e")
        
        ctk.CTkButton(f_botoes, text="ABRIR", width=60, height=24, fg_color="#34495e", 
                      command=lambda p=arquivo_path: self.abrir_arquivo(p)).pack(side="left", padx=5)
        
        btn_excluir = ctk.CTkButton(f_botoes, text="EXCLUIR", width=60, height=24, fg_color="#A30000",
                                    command=lambda p=arquivo_path: self.excluir_arquivo(p))
        btn_excluir.pack(side="left", padx=5)
        
        # Regra de Segurança do SISADAM: Apenas MASTER pode apagar do Cofre.
        if self.nivel != "MASTER":
            btn_excluir.configure(state="disabled", fg_color="#444")

    def abrir_arquivo(self, path):
        try:
            os.startfile(path)
        except Exception as e:
            messagebox.showerror("Erro de Acesso", f"Não foi possível abrir o documento:\n{e}")

    def excluir_arquivo(self, path):
        # Reforço de segurança via código
        if self.nivel != "MASTER":
            messagebox.showwarning("Acesso Negado", "Apenas o nível Master tem autorização para remover arquivos do Cofre.")
            return
            
        resposta = messagebox.askyesno("Confirmar Exclusão", f"Você está prestes a excluir definitivamente:\n{path.name}\n\nConfirma?")
        if resposta:
            try:
                os.remove(path)
                self.carregar_arquivos(self.filtro_var.get())
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao deletar arquivo:\n{e}")