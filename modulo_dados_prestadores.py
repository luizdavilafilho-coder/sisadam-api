import customtkinter as ctk
from tkinter import ttk, messagebox
import sqlite3
import pathlib
import os
import cv2
import threading
import winsound
from datetime import datetime
from PIL import Image
import tkinter.font as tkfont

# --- CONFIGURAÇÃO DE CAMINHOS ---
PASTA_BASE = pathlib.Path.home() / "Documents" / "SISADAM"
PASTA_BANCO = PASTA_BASE / "Arquivos_Banco"
PASTA_FOTOS = PASTA_BASE / "Fotos_Prestadores"
ARQUIVO_DB = PASTA_BANCO / "prestadores.db"
ARQUIVO_DB_MORADORES = PASTA_BANCO / "dados_moradores.db"

class BancoPrestadores(ctk.CTkFrame):
    def __init__(self, master, nivel="OPERADOR", usuario="USUÁRIO", **kwargs):
        # 1. Inicializa o Frame Pai
        super().__init__(master, **kwargs)
        
        # 2. Configurações de Identificação
        self.cor_destaque = "#F57C00"
        self.nivel = nivel.strip().upper()
        self.usuario_logado = usuario.upper()
        
        # 3. Variáveis de Estado
        self.id_em_edicao = None
        self.foto_temporaria = None 
        self.alarme_ativo = False
        self.img_tk = None
        
        # 4. Infraestrutura
        PASTA_BANCO.mkdir(parents=True, exist_ok=True)
        PASTA_FOTOS.mkdir(parents=True, exist_ok=True)
        
        self.criar_banco()
        self.configurar_estilos() 
        self.montar_interface()
        self.aplicar_permissoes()
        self.carregar_dados()

    def criar_banco(self):
        conn = sqlite3.connect(str(ARQUIVO_DB))
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute('''CREATE TABLE IF NOT EXISTS prestadores (
                            id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            empresa TEXT, prestador TEXT, documento TEXT,
                            local TEXT, bloco TEXT, apartamento TEXT,
                            autorizado_por TEXT, hora_entrada TEXT, hora_saida TEXT,
                            foto_path TEXT, cracha_entregue TEXT, cracha_devolvido TEXT)''')
        conn.commit()
        conn.close()

    def fechar_ciclo_diario(self):
        """Exportação automática dos prestadores para o Cofre à meia-noite"""
        try:
            import pandas as pd
            p_cofre = PASTA_BASE / "Cofre_Backup" / "Prestadores"
            p_cofre.mkdir(parents=True, exist_ok=True)
            ontem = (datetime.now() - (pathlib.timedelta(days=1) if hasattr(pathlib, 'timedelta') else __import__('datetime').timedelta(days=1))).strftime('%d-%m-%Y')
            caminho_excel = p_cofre / f"Relatorio_Prestadores_{ontem}.xlsx"
            conn = sqlite3.connect(str(ARQUIVO_DB))
            df = pd.read_sql_query("SELECT * FROM prestadores", conn)
            df.to_excel(caminho_excel, index=False)
            conn.close()
            self.carregar_dados()
            self.reset_total()
        except: pass

    def configurar_estilos(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="white", foreground="black", rowheight=30, fieldbackground="white", font=("Arial", 10))
        style.map("Treeview", background=[('selected', self.cor_destaque)], foreground=[('selected', 'black')])
        style.configure("Treeview.Heading", background="#222", foreground="white", relief="flat", font=("Arial", 10, "bold"))

    def montar_interface(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # LINHA 0: Título
        ctk.CTkLabel(self, text="SISADAM - CONTROLE DE PRESTADORES", 
                     font=("Roboto Mono", 22, "bold"), 
                     text_color=self.cor_destaque).grid(row=0, column=0, pady=(15, 0))

        # LINHA 1: Identificação do Usuário (Logado Como)
        self.lbl_user_info = ctk.CTkLabel(self, text=f"LOGADO COMO: {self.usuario_logado} [{self.nivel}]", 
                                          font=("Arial", 11, "bold"), 
                                          text_color="#FFFFFF")
        self.lbl_user_info.grid(row=1, column=0, pady=(0, 15))

        # LINHA 2: Área de Dados e Foto
        self.f_topo = ctk.CTkFrame(self, fg_color="transparent")
        self.f_topo.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        self.f_topo.grid_columnconfigure(0, weight=1)

        # Quadro de Dados (Esquerda)
        self.f_dados = ctk.CTkFrame(self.f_topo, fg_color="#121212", corner_radius=10, border_width=1, border_color="#333")
        self.f_dados.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        estilo_in = {"fg_color": "white", "text_color": "black", "placeholder_text_color": "gray"}

        self.ent_empresa = ctk.CTkEntry(self.f_dados, placeholder_text="EMPRESA", width=200, **estilo_in)
        self.ent_empresa.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.ent_prestador = ctk.CTkEntry(self.f_dados, placeholder_text="NOME DO PRESTADOR", width=300, **estilo_in)
        self.ent_prestador.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky="w")
        self.ent_doc = ctk.CTkEntry(self.f_dados, placeholder_text="RG / CPF", width=150, **estilo_in)
        self.ent_doc.grid(row=1, column=3, padx=10, pady=10, sticky="w")

        self.ent_local = ctk.CTkComboBox(self.f_dados, values=["APARTAMENTO", "CONDOMÍNIO"], width=150, fg_color="white", text_color="black")
        self.ent_local.set("LOCAL"); self.ent_local.grid(row=2, column=0, padx=10, pady=10, sticky="w")

        self.f_bloco_apto = ctk.CTkFrame(self.f_dados, fg_color="transparent")
        self.f_bloco_apto.grid(row=2, column=1, padx=10, pady=10, sticky="w")
        self.ent_bloco = ctk.CTkComboBox(self.f_bloco_apto, values=["BLOCO A", "BLOCO B", "N/A"], width=100, fg_color="white", text_color="black", command=self.buscar_morador_autorizador)
        self.ent_bloco.set("BLOCO"); self.ent_bloco.pack(side="left", padx=(0, 5))
        self.ent_apt = ctk.CTkEntry(self.f_bloco_apto, placeholder_text="APTO", width=70, **estilo_in)
        self.ent_apt.pack(side="left")
        self.ent_apt.bind("<KeyRelease>", self.buscar_morador_autorizador)

        self.cb_autorizado = ctk.CTkComboBox(self.f_dados, values=["AUTORIZADO POR..."], width=250, fg_color="white", text_color="black")
        self.cb_autorizado.set("AUTORIZADO POR..."); self.cb_autorizado.grid(row=2, column=2, columnspan=2, padx=10, pady=10, sticky="w")

        self.f_crachas = ctk.CTkFrame(self.f_dados, fg_color="transparent")
        self.f_crachas.grid(row=3, column=0, columnspan=4, padx=10, pady=10, sticky="w")
        ctk.CTkLabel(self.f_crachas, text="CRACHÁ ENTREGUE?").pack(side="left", padx=(0, 5))
        self.cb_entregue = ctk.CTkOptionMenu(self.f_crachas, values=["NÃO", "SIM"], width=80, fg_color="#333", button_color=self.cor_destaque, command=self.parar_alarme)
        self.cb_entregue.set("NÃO"); self.cb_entregue.pack(side="left", padx=(0, 20))
        ctk.CTkLabel(self.f_crachas, text="CRACHÁ DEVOLVIDO?").pack(side="left", padx=(0, 5))
        self.cb_devolvido = ctk.CTkOptionMenu(self.f_crachas, values=["NÃO", "SIM"], width=80, fg_color="#333", button_color="#2E7D32", command=self.parar_alarme)
        self.cb_devolvido.set("NÃO"); self.cb_devolvido.pack(side="left")

        self.f_acoes = ctk.CTkFrame(self.f_dados, fg_color="transparent")
        self.f_acoes.grid(row=4, column=0, columnspan=4, padx=10, pady=(15, 10), sticky="ew")
        ctk.CTkButton(self.f_acoes, text="+ NOVO", fg_color="#555", command=self.reset_total, width=90).pack(side="left", padx=5)
        ctk.CTkButton(self.f_acoes, text="SALVAR / ENTRADA", fg_color=self.cor_destaque, text_color="black", font=("Arial", 11, "bold"), command=self.salvar_registro).pack(side="left", padx=5)
        ctk.CTkButton(self.f_acoes, text="📸 FOTO", fg_color="#5D4037", command=self.tirar_foto, width=90).pack(side="left", padx=5)
        ctk.CTkButton(self.f_acoes, text="REGISTRAR SAÍDA", fg_color="#2E7D32", command=self.registrar_saida).pack(side="left", padx=5)
        self.btn_editar = ctk.CTkButton(self.f_acoes, text="EDITAR", fg_color="#1E88E5", command=self.carregar_edicao, width=90)
        self.btn_editar.pack(side="left", padx=5)
        self.btn_deletar = ctk.CTkButton(self.f_acoes, text="DELETAR", fg_color="#D32F2F", command=self.deletar_registro, width=90)
        self.btn_deletar.pack(side="right", padx=5)

        # Quadro da Foto (Direita)
        self.f_foto = ctk.CTkFrame(self.f_topo, width=240, height=260, fg_color="#121212", corner_radius=10, border_width=1, border_color=self.cor_destaque)
        self.f_foto.grid(row=0, column=1, sticky="ns"); self.f_foto.grid_propagate(False)
        ctk.CTkLabel(self.f_foto, text="IDENTIFICAÇÃO VISUAL", text_color=self.cor_destaque, font=("Arial", 10, "bold")).pack(pady=10)
        self.label_preview = ctk.CTkLabel(self.f_foto, text="SEM FOTO", width=200, height=200, fg_color="#1E1E1E", corner_radius=8)
        self.label_preview.pack(pady=5, padx=20)

        # LINHA 3: Tabela
        self.f_tabela = ctk.CTkFrame(self, fg_color="transparent")
        self.f_tabela.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.colunas = ("ID", "Prestador", "Empresa", "Doc.", "Local", "Bl/Ap", "Autorizado", "Entrada", "Saída")
        self.tabela = ttk.Treeview(self.f_tabela, columns=self.colunas, show="headings")
        sc_v = ttk.Scrollbar(self.f_tabela, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=sc_v.set)
        for col in self.colunas:
            self.tabela.heading(col, text=col)
            self.tabela.column(col, width=100, anchor="center")
        sc_v.pack(side="right", fill="y"); self.tabela.pack(side="left", fill="both", expand=True)
        self.tabela.bind("<<TreeviewSelect>>", self.ao_selecionar)

    def buscar_morador_autorizador(self, event=None):
        bloco, apto = self.ent_bloco.get(), self.ent_apt.get().strip()
        if bloco != "BLOCO" and apto:
            try:
                conn = sqlite3.connect(str(ARQUIVO_DB_MORADORES))
                cur = conn.execute("SELECT nome_morador FROM moradores WHERE bloco=? AND apartamento=?", (bloco, apto))
                res = [r[0] for r in cur.fetchall()]
                conn.close()
                if res: self.cb_autorizado.configure(values=res); self.cb_autorizado.set(res[0])
                else: self.cb_autorizado.configure(values=["NÃO ENCONTRADO"]); self.cb_autorizado.set("NÃO ENCONTRADO")
            except: pass

    def salvar_registro(self):
        if not self.id_em_edicao and self.cb_entregue.get() == "NÃO":
            messagebox.showwarning("SEGURANÇA", "ENTREGUE O CRACHÁ!"); return
        autorizador = self.cb_autorizado.get().upper()
        if autorizador in ["AUTORIZADO POR...", "NÃO ENCONTRADO"]: autorizador = ""
        dados = (self.ent_empresa.get().upper(), self.ent_prestador.get().upper(), self.ent_doc.get().upper(),
                 self.ent_local.get(), self.ent_bloco.get(), self.ent_apt.get().upper(), autorizador, 
                 self.cb_entregue.get(), self.cb_devolvido.get(), self.foto_temporaria)
        if not dados[1]: return
        conn = sqlite3.connect(str(ARQUIVO_DB))
        if self.id_em_edicao:
            conn.execute('''UPDATE prestadores SET empresa=?, prestador=?, documento=?, local=?, bloco=?, 
                            apartamento=?, autorizado_por=?, cracha_entregue=?, cracha_devolvido=?, foto_path=? WHERE id=?''', 
                            (*dados, self.id_em_edicao))
        else:
            hora = datetime.now().strftime("%d/%m/%Y %H:%M")
            conn.execute('''INSERT INTO prestadores (empresa, prestador, documento, local, bloco, apartamento, 
                            autorizado_por, cracha_entregue, cracha_devolvido, foto_path, hora_entrada, hora_saida) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (*dados, hora, "---"))
        conn.commit(); conn.close(); self.reset_total(); self.carregar_dados()

    def registrar_saida(self):
        if self.cb_devolvido.get() == "NÃO":
            messagebox.showwarning("SEGURANÇA", "RECOLHA O CRACHÁ!"); return
        sel = self.tabela.selection()
        if not sel: return
        id_reg = self.tabela.item(sel[0])['values'][0]
        hora = datetime.now().strftime("%d/%m/%Y %H:%M")
        conn = sqlite3.connect(str(ARQUIVO_DB))
        conn.execute("UPDATE prestadores SET hora_saida=?, cracha_devolvido='SIM' WHERE id=?", (hora, id_reg))
        conn.commit(); conn.close(); self.carregar_dados()

    def carregar_dados(self):
        for i in self.tabela.get_children(): self.tabela.delete(i)
        conn = sqlite3.connect(str(ARQUIVO_DB))
        cursor = conn.execute("SELECT id, prestador, empresa, documento, local, bloco || '-' || apartamento, autorizado_por, hora_entrada, hora_saida FROM prestadores ORDER BY id DESC")
        for r in cursor.fetchall(): self.tabela.insert("", "end", values=r)
        conn.close()

    def tirar_foto(self):
        cap = cv2.VideoCapture(0)
        while True:
            ret, frame = cap.read()
            cv2.imshow("SISADAM - [ESPACO] Foto", frame)
            if cv2.waitKey(1) == 32:
                path = PASTA_FOTOS / f"P_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                cv2.imwrite(str(path), frame); self.foto_temporaria = str(path)
                self.atualizar_foto_lateral(str(path)); break
            if cv2.waitKey(1) == 27: break
        cap.release(); cv2.destroyAllWindows()

    def atualizar_foto_lateral(self, caminho):
        if caminho and os.path.exists(caminho):
            img = Image.open(caminho); img.thumbnail((200, 200))
            self.img_tk = ctk.CTkImage(img, size=(img.width, img.height))
            self.label_preview.configure(image=self.img_tk, text="")
        else: self.label_preview.configure(image=None, text="SEM FOTO")

    def ao_selecionar(self, event):
        sel = self.tabela.selection()
        if sel:
            id_reg = self.tabela.item(sel[0])['values'][0]
            conn = sqlite3.connect(str(ARQUIVO_DB))
            res = conn.execute("SELECT foto_path FROM prestadores WHERE id=?", (id_reg,)).fetchone()
            conn.close()
            if res: self.atualizar_foto_lateral(res[0])

    def carregar_edicao(self):
        sel = self.tabela.selection()
        if not sel: return
        id_reg = self.tabela.item(sel[0])['values'][0]
        conn = sqlite3.connect(str(ARQUIVO_DB))
        res = conn.execute("SELECT * FROM prestadores WHERE id=?", (id_reg,)).fetchone()
        conn.close()
        if res:
            self.id_em_edicao = res[0]
            self.ent_empresa.delete(0, 'end'); self.ent_empresa.insert(0, res[1])
            self.ent_prestador.delete(0, 'end'); self.ent_prestador.insert(0, res[2])
            self.ent_doc.delete(0, 'end'); self.ent_doc.insert(0, res[3] or "")
            self.ent_local.set(res[4] or "LOCAL"); self.ent_bloco.set(res[5] or "BLOCO")
            self.ent_apt.delete(0, 'end'); self.ent_apt.insert(0, res[6] or "")
            self.cb_autorizado.set(res[7] or "AUTORIZADO POR...")
            self.cb_entregue.set(res[11] or "NÃO"); self.cb_devolvido.set(res[12] or "NÃO")
            self.foto_temporaria = res[10]; self.atualizar_foto_lateral(res[10])

    def reset_total(self):
        for e in [self.ent_empresa, self.ent_prestador, self.ent_doc, self.ent_apt]: e.delete(0, 'end')
        self.ent_local.set("LOCAL"); self.ent_bloco.set("BLOCO"); self.cb_autorizado.set("AUTORIZADO POR...")
        self.cb_entregue.set("NÃO"); self.cb_devolvido.set("NÃO"); self.id_em_edicao = None; self.foto_temporaria = None
        self.label_preview.configure(image=None, text="SEM FOTO")

    def deletar_registro(self):
        if self.nivel != "MASTER": return
        sel = self.tabela.selection()
        if sel and messagebox.askyesno("Atenção", "Excluir permanentemente?"):
            conn = sqlite3.connect(str(ARQUIVO_DB))
            conn.execute("DELETE FROM prestadores WHERE id=?", (self.tabela.item(sel[0])['values'][0],))
            conn.commit(); conn.close(); self.carregar_dados()

    def parar_alarme(self, *args): self.alarme_ativo = False
    def aplicar_permissoes(self):
        if self.nivel in ["OPERADOR", "ADMIN"]:
            self.btn_editar.configure(state="disabled", fg_color="#444")
            self.btn_deletar.configure(state="disabled", fg_color="#444")