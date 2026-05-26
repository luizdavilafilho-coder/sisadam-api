import customtkinter as ctk
from tkinter import ttk, messagebox
import sqlite3
import pathlib
import os
import cv2
import threading
from datetime import datetime
from PIL import Image
import tkinter.font as tkfont
import firebase_admin
from firebase_admin import credentials, messaging

# --- CONFIGURAÇÃO DE CAMINHOS ---
PASTA_BASE = pathlib.Path.home() / "Documents" / "SISADAM"
PASTA_BANCO = PASTA_BASE / "Arquivos_Banco"
PASTA_FOTOS_ENTREGAS = PASTA_BASE / "Fotos_Entregas"
ARQUIVO_DB_ENTREGAS = PASTA_BANCO / "dados_entregas.db"
ARQUIVO_DB_MORADORES = PASTA_BANCO / "dados_moradores.db"
ARQUIVO_DB_SENHAS = PASTA_BANCO / "dados_senhas_entregas.db"
CAMINHO_CHAVE_FCM = PASTA_BASE / "sisadam-firebase-adminsdk.json"

class BancoEntregas(ctk.CTkFrame):
    def __init__(self, master, nivel="OPERADOR", **kwargs):
        super().__init__(master, **kwargs)
        self.cor_destaque = "#F57C00"
        self.nivel = nivel.strip().upper()
        self.id_em_edicao = None
        self.foto_entregador = None
        self.foto_pacote = None
        self.moradores_atuais = {} 
        
        PASTA_BANCO.mkdir(parents=True, exist_ok=True)
        PASTA_FOTOS_ENTREGAS.mkdir(parents=True, exist_ok=True)
        
        self.inicializar_firebase()
        self.inicializar_banco()
        self.configurar_estilos()
        self.montar_interface()

    def inicializar_firebase(self):
        """Inicializa a conexão com os servidores do Google/FCM"""
        try:
            if not firebase_admin._apps:
                if CAMINHO_CHAVE_FCM.exists():
                    cred = credentials.Certificate(str(CAMINHO_CHAVE_FCM))
                    firebase_admin.initialize_app(cred)
                else:
                    print(f"⚠️ AVISO: Arquivo de credenciais FCM não encontrado em: {CAMINHO_CHAVE_FCM}")
        except Exception as e:
            print(f"Erro ao inicializar Firebase FCM: {e}")

    def inicializar_banco(self):
        conn = sqlite3.connect(str(ARQUIVO_DB_ENTREGAS))
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("CREATE TABLE IF NOT EXISTS entregas (id INTEGER PRIMARY KEY AUTOINCREMENT)")
        colunas = [
            ("empresa", "TEXT"), ("entregador", "TEXT"), ("documento", "TEXT"),
            ("bloco", "TEXT"), ("apartamento", "TEXT"), ("tipo_volume", "TEXT"), 
            ("status", "TEXT"), ("data_entrada", "TEXT"), 
            ("foto_entregador", "TEXT"), ("foto_pacote", "TEXT"),
            ("retirado_por", "TEXT"), ("data_retirada", "TEXT"), ("destinatario", "TEXT") 
        ]
        for col, tipo in colunas:
            try: conn.execute(f"ALTER TABLE entregas ADD COLUMN {col} {tipo}")
            except sqlite3.OperationalError: pass
        conn.commit(); conn.close()

        # Preparar banco de moradores para receber o Token do Web App
        conn_m = sqlite3.connect(str(ARQUIVO_DB_MORADORES))
        try: conn_m.execute("ALTER TABLE moradores ADD COLUMN fcm_token TEXT")
        except sqlite3.OperationalError: pass
        conn_m.commit(); conn_m.close()

        conn_s = sqlite3.connect(str(ARQUIVO_DB_SENHAS))
        conn_s.execute("CREATE TABLE IF NOT EXISTS senhas (bloco TEXT, apartamento TEXT, empresa TEXT, senha TEXT, PRIMARY KEY(bloco, apartamento, empresa))")
        conn_s.commit(); conn_s.close()

    def fechar_ciclo_diario(self):
        """Exportação automática e silenciosa para o Cofre à meia-noite"""
        try:
            import pandas as pd
            from datetime import timedelta
            
            p_cofre = PASTA_BASE / "Cofre_Backup" / "Entregas"
            p_cofre.mkdir(parents=True, exist_ok=True)
            
            ontem = (datetime.now() - timedelta(days=1)).strftime('%d-%m-%Y')
            caminho_excel = p_cofre / f"Backup_Automatico_Entregas_{ontem}.xlsx"
            
            conn = sqlite3.connect(str(ARQUIVO_DB_ENTREGAS))
            df = pd.read_sql_query("SELECT * FROM entregas", conn)
            df.to_excel(caminho_excel, index=False)
            conn.close()
            
            self.carregar_dados()
            self.nova_entrada()
            print(f"Fechamento 24h concluído: {caminho_excel}")
        except Exception as e:
            print(f"Erro no fechamento automático: {e}")

    def configurar_estilos(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="white", foreground="black", rowheight=30, fieldbackground="white")
        style.map("Treeview", background=[('selected', self.cor_destaque)], foreground=[('selected', 'black')])
        style.configure("Treeview.Heading", background="#222", foreground="white", font=("Arial", 10, "bold"))

    def verificar_senha_cadastrada(self, *args):
        try:
            bloco, apto, empresa = self.ent_bloco.get(), self.ent_apt.get().strip(), self.ent_empresa.get().upper()
            destinatario = self.cb_destinatario.get()
            
            if destinatario not in ["DESTINATÁRIO", "DIGITE O APTO", "NÃO LOCALIZADO"] and empresa:
                conn = sqlite3.connect(str(ARQUIVO_DB_SENHAS))
                res = conn.execute("SELECT senha FROM senhas WHERE bloco=? AND apartamento=? AND empresa=?", (bloco, apto, empresa)).fetchone()
                conn.close()
                if res:
                    self.ent_senha_app.configure(state="normal", fg_color="#FFF9C4") 
                    self.ent_senha_app.delete(0, 'end')
                    self.ent_senha_app.insert(0, res[0])
                    self.lbl_aviso_senha.configure(text="⚠️ SENHA LOCALIZADA!", text_color="#D32F2F")
                else:
                    self.ent_senha_app.delete(0, 'end')
                    self.ent_senha_app.configure(state="normal", fg_color="white")
                    self.lbl_aviso_senha.configure(text="Sem senha registrada", text_color="gray")
            else:
                self.ent_senha_app.delete(0, 'end')
                self.ent_senha_app.configure(state="disabled", fg_color="#E0E0E0")
                self.lbl_aviso_senha.configure(text="Identifique o recebedor primeiro", text_color="gray")
        except: pass

    def buscar_moradores_unidade(self, *args):
        try:
            bloco, apto = self.ent_bloco.get(), self.ent_apt.get().strip()
            if bloco == "BLOCO" or len(apto) < 1:
                self.cb_destinatario.configure(state="normal"); self.cb_destinatario.set("DESTINATÁRIO"); self.cb_destinatario.configure(state="disabled")
                return
            conn = sqlite3.connect(str(ARQUIVO_DB_MORADORES))
            # Busca o nome do morador e o Token FCM gerado pelo Web App
            rows = conn.execute("SELECT nome_morador, fcm_token FROM moradores WHERE bloco=? AND apartamento=?", (bloco, apto)).fetchall()
            conn.close()
            
            self.moradores_atuais = {}
            nomes = ["TITULAR DO APTO", "OUTRO / VISITANTE"]
            if rows:
                for r in rows:
                    nome = r[0].upper()
                    token_fcm = r[1]
                    self.moradores_atuais[nome] = token_fcm
                    nomes.append(nome)
                self.cb_destinatario.configure(state="normal"); self.cb_destinatario.configure(values=nomes); self.cb_destinatario.set(nomes[0])
        except: pass

    def montar_interface(self):
        for widget in self.winfo_children(): widget.destroy()
        
        ctk.CTkLabel(self, text="SISADAM - CONTROLE DE ENTREGAS", font=("Roboto Mono", 22, "bold"), text_color=self.cor_destaque).pack(pady=(10, 0))
        
        self.lbl_user_info = ctk.CTkLabel(self, text=f"LOGADO COMO: {self.nivel}", font=("Arial", 12, "bold"), text_color="white")
        self.lbl_user_info.pack(pady=(0, 10))

        self.f_superior = ctk.CTkFrame(self, fg_color="transparent")
        self.f_superior.pack(fill="x", padx=10, pady=5)

        self.f_dados_col = ctk.CTkFrame(self.f_superior, fg_color="transparent")
        self.f_dados_col.pack(side="left", fill="both", expand=True)

        estilo_in = {"fg_color": "white", "text_color": "black", "placeholder_text_color": "gray"}
        self.f_campos = ctk.CTkFrame(self.f_dados_col, fg_color="#121212", corner_radius=10, border_width=1, border_color="#333")
        self.f_campos.pack(fill="both", expand=True)

        self.ent_empresa = ctk.CTkEntry(self.f_campos, placeholder_text="EMPRESA / APP", width=250, **estilo_in)
        self.ent_empresa.grid(row=0, column=0, padx=10, pady=10)
        self.ent_empresa.bind("<KeyRelease>", self.verificar_senha_cadastrada)
        
        self.ent_entregador = ctk.CTkEntry(self.f_campos, placeholder_text="NOME ENTREGADOR", width=350, **estilo_in)
        self.ent_entregador.grid(row=0, column=1, columnspan=2, padx=10, pady=10, sticky="w")

        self.ent_bloco = ctk.CTkComboBox(self.f_campos, values=["BLOCO A", "BLOCO B"], width=120, fg_color="white", text_color="black", command=self.buscar_moradores_unidade)
        self.ent_bloco.set("BLOCO"); self.ent_bloco.grid(row=1, column=0, padx=10, pady=10)
        
        self.var_apto = ctk.StringVar()
        self.var_apto.trace_add("write", self.buscar_moradores_unidade)
        self.ent_apt = ctk.CTkEntry(self.f_campos, textvariable=self.var_apto, placeholder_text="APTO", width=80, **estilo_in)
        self.ent_apt.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        self.cb_destinatario = ctk.CTkComboBox(self.f_campos, values=["DIGITE O APTO"], width=230, fg_color="white", text_color="black", command=self.verificar_senha_cadastrada)
        self.cb_destinatario.set("DESTINATÁRIO"); self.cb_destinatario.configure(state="disabled")
        self.cb_destinatario.grid(row=1, column=2, padx=10, pady=10, sticky="w")
        
        self.cb_volume = ctk.CTkComboBox(self.f_campos, values=["ENVELOPE", "CAIXA PEQUENA", "CAIXA GRANDE", "IFOOD", "REMÉDIO REFRIGERADO", "OUTROS"], width=200, fg_color="white", text_color="black")
        self.cb_volume.set("TIPO DE VOLUME"); self.cb_volume.grid(row=1, column=3, padx=10, pady=10, sticky="w")

        self.f_linha2 = ctk.CTkFrame(self.f_campos, fg_color="transparent")
        self.f_linha2.grid(row=2, column=0, columnspan=4, sticky="w", padx=10, pady=5)
        
        self.cb_status = ctk.CTkComboBox(self.f_linha2, values=["AGUARDANDO RETIRADA", "ENTREGUE", "DEVOLVIDO"], width=200, fg_color="white", text_color="black")
        self.cb_status.set("AGUARDANDO RETIRADA"); self.cb_status.pack(side="left", padx=(0,10))
        
        self.ent_senha_app = ctk.CTkEntry(self.f_linha2, placeholder_text="CÓDIGO APP", width=120, fg_color="#E0E0E0", text_color="black", font=("Arial", 12, "bold"), state="disabled")
        self.ent_senha_app.pack(side="left", padx=5)
        
        ctk.CTkButton(self.f_linha2, text="💾 SALVAR SENHA", width=110, height=28, fg_color="#388E3C", command=self.salvar_senha_nova).pack(side="left", padx=5)
        self.lbl_aviso_senha = ctk.CTkLabel(self.f_linha2, text="Identifique o recebedor primeiro", font=("Arial", 10), text_color="gray")
        self.lbl_aviso_senha.pack(side="left", padx=5)

        self.f_lateral = ctk.CTkFrame(self.f_superior, width=450, fg_color="#121212", border_width=1, border_color="#333", corner_radius=10)
        self.f_lateral.pack(side="right", fill="y", padx=(10, 0))
        
        self.f_fotos_internas = ctk.CTkFrame(self.f_lateral, fg_color="transparent")
        self.f_fotos_internas.pack(expand=True)

        self.label_preview_entregador = ctk.CTkLabel(self.f_fotos_internas, text="FOTO ENTREGADOR", width=200, height=130, fg_color="#1E1E1E", corner_radius=8, font=("Arial", 10))
        self.label_preview_entregador.grid(row=0, column=0, padx=10, pady=10)
        
        self.label_preview_pacote = ctk.CTkLabel(self.f_fotos_internas, text="FOTO PACOTE", width=200, height=130, fg_color="#1E1E1E", corner_radius=8, font=("Arial", 10))
        self.label_preview_pacote.grid(row=0, column=1, padx=10, pady=10)

        self.f_acoes = ctk.CTkFrame(self, fg_color="transparent")
        self.f_acoes.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(self.f_acoes, text="➕ NOVA", width=90, fg_color="#2196F3", command=self.nova_entrada).pack(side="left", padx=2)
        self.btn_g = ctk.CTkButton(self.f_acoes, text="💾 GRAVAR", width=90, fg_color=self.cor_destaque, text_color="black", command=self.salvar_registro)
        self.btn_g.pack(side="left", padx=2)
        ctk.CTkButton(self.f_acoes, text="📸 ENT.", width=80, fg_color="#5D4037", command=lambda: self.tirar_foto("entregador")).pack(side="left", padx=2)
        ctk.CTkButton(self.f_acoes, text="📸 PAC.", width=80, fg_color="#6D4C41", command=lambda: self.tirar_foto("pacote")).pack(side="left", padx=2)
        
        # Novo Botão de Disparo FCM substituindo o WhatsApp
        ctk.CTkButton(self.f_acoes, text="🔔 AVISAR", width=80, fg_color="#FF7043", command=self.preparar_fcm).pack(side="left", padx=2)
        
        ctk.CTkButton(self.f_acoes, text="📦 RETIRADA", width=100, fg_color="#8E24AA", command=self.registrar_retirada).pack(side="left", padx=2)
        ctk.CTkButton(self.f_acoes, text="EDITAR", width=80, fg_color="#0056b3", command=self.preparar_edicao).pack(side="left", padx=2)
        ctk.CTkButton(self.f_acoes, text="EXCLUIR", width=80, fg_color="#A30000", command=self.deletar_registro).pack(side="left", padx=2)

        # Nova barra de progresso para o FCM
        self.f_status_fcm = ctk.CTkFrame(self, fg_color="transparent")
        self.f_status_fcm.pack(fill="x", padx=10)
        self.progresso_fcm = ctk.CTkProgressBar(self.f_status_fcm, width=300, height=8); self.progresso_fcm.set(0); self.progresso_fcm.pack(side="left", padx=5)
        self.lbl_status_fcm = ctk.CTkLabel(self.f_status_fcm, text="AGUARDANDO", font=("Arial", 9), text_color="gray"); self.lbl_status_fcm.pack(side="left")

        self.f_tab = ctk.CTkFrame(self, fg_color="transparent")
        self.f_tab.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        cols = ("ID", "Empresa", "Entregador", "Bloco", "Apto", "Para", "Status", "QUEM RETIROU", "Dt. Entrada", "Dt. Retirada")
        self.tree = ttk.Treeview(self.f_tab, columns=cols, show="headings", height=12)
        for c in cols: self.tree.heading(c, text=c.upper()); self.tree.column(c, width=100, anchor="center")
        
        vsb = ttk.Scrollbar(self.f_tab, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.f_tab, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        self.f_tab.grid_columnconfigure(0, weight=1)
        self.f_tab.grid_rowconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self.ao_selecionar)
        self.carregar_dados()

    def ajustar_colunas(self):
        for col in self.tree['columns']:
            largura_maxima = tkfont.Font().measure(col.upper()) + 25
            for item in self.tree.get_children():
                texto_celula = str(self.tree.set(item, col))
                largura_celula = tkfont.Font().measure(texto_celula) + 25
                if largura_celula > largura_maxima:
                    largura_maxima = largura_celula
            self.tree.column(col, width=largura_maxima)

    def carregar_dados(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        conn = sqlite3.connect(str(ARQUIVO_DB_ENTREGAS))
        cur = conn.execute("SELECT id, empresa, entregador, bloco, apartamento, destinatario, status, retirado_por, data_entrada, data_retirada FROM entregas ORDER BY id DESC")
        for r in cur.fetchall():
            linha = list(r)
            linha[7] = linha[7] if linha[7] else "-"
            linha[9] = linha[9] if linha[9] else "-"
            self.tree.insert("", "end", values=linha)
        conn.close()
        self.ajustar_colunas()

    def salvar_registro(self):
        nome_ent = self.ent_entregador.get().upper()
        if not nome_ent: return
        conn = sqlite3.connect(str(ARQUIVO_DB_ENTREGAS))
        dados = (self.ent_empresa.get().upper(), nome_ent, "", self.ent_bloco.get(), self.ent_apt.get().upper(), self.cb_volume.get(), self.cb_status.get(), self.foto_entregador, self.foto_pacote, self.cb_destinatario.get())
        if self.id_em_edicao:
            conn.execute("UPDATE entregas SET empresa=?, entregador=?, documento=?, bloco=?, apartamento=?, tipo_volume=?, status=?, foto_entregador=?, foto_pacote=?, destinatario=? WHERE id=?", dados + (self.id_em_edicao,))
        else:
            conn.execute("INSERT INTO entregas (empresa, entregador, documento, bloco, apartamento, tipo_volume, status, foto_entregador, foto_pacote, destinatario, data_entrada) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (*dados, datetime.now().strftime('%d/%m/%Y %H:%M')))
        conn.commit(); conn.close(); self.carregar_dados(); self.nova_entrada()

    def nova_entrada(self):
        self.var_apto.set(""); [e.delete(0, 'end') for e in [self.ent_empresa, self.ent_entregador, self.ent_senha_app]]
        self.ent_bloco.set("BLOCO"); self.cb_destinatario.configure(state="normal"); self.cb_destinatario.set("DESTINATÁRIO"); self.cb_destinatario.configure(state="disabled")
        self.foto_entregador, self.foto_pacote, self.id_em_edicao = None, None, None
        self.label_preview_entregador.configure(image=None, text="FOTO ENTREGADOR"); self.label_preview_pacote.configure(image=None, text="FOTO PACOTE")
        self.btn_g.configure(text="💾 GRAVAR", fg_color=self.cor_destaque, text_color="black")
        self.progresso_fcm.set(0)
        self.lbl_status_fcm.configure(text="AGUARDANDO", text_color="gray")

    def tirar_foto(self, tipo):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened(): cap = cv2.VideoCapture(0)
        while True:
            ret, frame = cap.read()
            if not ret: break
            cv2.imshow(f"CAPTURANDO {tipo.upper()}", frame)
            k = cv2.waitKey(1)
            if k == 32:
                ts = datetime.now().strftime('%H%M%S')
                path = PASTA_FOTOS_ENTREGAS / f"ENT_{tipo.upper()}_{ts}.jpg"
                cv2.imwrite(str(path), frame)
                if tipo == "entregador": self.foto_entregador = str(path)
                else: self.foto_pacote = str(path)
                self.atualizar_preview(); break
            if k == 27: break
        cap.release(); cv2.destroyAllWindows()

    def atualizar_preview(self):
        if self.foto_entregador and os.path.exists(self.foto_entregador):
            img = Image.open(self.foto_entregador); img.thumbnail((200, 130))
            self.label_preview_entregador.configure(image=ctk.CTkImage(img, size=(img.width, img.height)), text="")
        if self.foto_pacote and os.path.exists(self.foto_pacote):
            img = Image.open(self.foto_pacote); img.thumbnail((200, 130))
            self.label_preview_pacote.configure(image=ctk.CTkImage(img, size=(img.width, img.height)), text="")

    def preparar_fcm(self):
        """Inicia a thread para não travar a interface durante o envio pela internet"""
        threading.Thread(target=self.rotina_fcm, daemon=True).start()

    def rotina_fcm(self):
        destinatario = self.cb_destinatario.get()
        token_fcm = self.moradores_atuais.get(destinatario)
        
        self.lbl_status_fcm.configure(text="⚙️ COMUNICANDO COM SERVIDOR PUSH...", text_color="#FF7043")
        self.progresso_fcm.set(0.4)

        if not token_fcm:
            self.progresso_fcm.set(0)
            self.lbl_status_fcm.configure(text="❌ SEM TOKEN CADASTRADO", text_color="#D32F2F")
            messagebox.showwarning("Aviso do Sistema", "O morador selecionado não possui o Web App configurado (Token FCM ausente).")
            return

        try:
            empresa = self.ent_empresa.get().upper()
            tipo_vol = self.cb_volume.get()
            
            mensagem = messaging.Message(
                notification=messaging.Notification(
                    title="📦 Nova Encomenda na Portaria!",
                    body=f"Um pacote da {empresa} ({tipo_vol}) acaba de ser registrado pelo porteiro."
                ),
                token=token_fcm,
            )
            
            resposta = messaging.send(mensagem)
            
            self.progresso_fcm.set(1.0)
            self.lbl_status_fcm.configure(text="✅ NOTIFICAÇÃO ENVIADA COM SUCESSO!", text_color="#00E676")
            print(f"Sucesso FCM ID: {resposta}")
            
        except Exception as e:
            self.progresso_fcm.set(0)
            self.lbl_status_fcm.configure(text="❌ FALHA AO ENVIAR", text_color="#D32F2F")
            print(f"Erro ao enviar Firebase Push: {e}")
            messagebox.showerror("Erro FCM", f"Falha ao comunicar com os servidores do Google:\n{e}")

    def ao_selecionar(self, event):
        sel = self.tree.selection()
        if sel:
            id_sel = self.tree.item(sel[0])['values'][0]
            conn = sqlite3.connect(str(ARQUIVO_DB_ENTREGAS))
            res = conn.execute("SELECT foto_entregador, foto_pacote FROM entregas WHERE id=?", (id_sel,)).fetchone()
            conn.close()
            if res: 
                self.foto_entregador, self.foto_pacote = res[0], res[1]
                self.atualizar_preview()

    def registrar_retirada(self):
        sel = self.tree.selection()
        if not sel: return
        id_reg = self.tree.item(sel[0])['values'][0]
        quem = ctk.CTkInputDialog(text="Quem retirou?", title="Retirada").get_input()
        if quem:
            conn = sqlite3.connect(str(ARQUIVO_DB_ENTREGAS))
            conn.execute("UPDATE entregas SET status='ENTREGUE', retirado_por=?, data_retirada=? WHERE id=?", (quem.upper(), datetime.now().strftime('%d/%m/%Y %H:%M'), id_reg))
            conn.commit(); conn.close(); self.carregar_dados()

    def preparar_edicao(self):
        sel = self.tree.selection()
        if not sel: return
        id_sel = self.tree.item(sel[0])['values'][0]
        self.nova_entrada(); self.id_em_edicao = id_sel
        conn = sqlite3.connect(str(ARQUIVO_DB_ENTREGAS))
        d = conn.execute("SELECT empresa, entregador, bloco, apartamento, tipo_volume, status, foto_entregador, foto_pacote, destinatario FROM entregas WHERE id=?", (id_sel,)).fetchone()
        conn.close()
        if d:
            self.ent_empresa.insert(0, d[0]); self.ent_entregador.insert(0, d[1])
            self.ent_bloco.set(d[2]); self.var_apto.set(d[3]); self.cb_volume.set(d[4]); self.cb_status.set(d[5])
            self.foto_entregador, self.foto_pacote = d[6], d[7]; self.cb_destinatario.set(d[8]); self.atualizar_preview()
            self.btn_g.configure(text="💾 ATUALIZAR", fg_color="#28a745", text_color="white")

    def deletar_registro(self):
        sel = self.tree.selection()
        if sel and messagebox.askyesno("Aviso", "Excluir permanentemente este registro?"):
            conn = sqlite3.connect(str(ARQUIVO_DB_ENTREGAS))
            conn.execute("DELETE FROM entregas WHERE id=?", (self.tree.item(sel[0])['values'][0],))
            conn.commit(); conn.close(); self.carregar_dados(); self.nova_entrada()

    def salvar_senha_nova(self):
        bloco, apto, empresa, senha = self.ent_bloco.get(), self.ent_apt.get().strip(), self.ent_empresa.get().upper(), self.ent_senha_app.get().strip()
        if bloco == "BLOCO" or not apto or not empresa: return
        conn = sqlite3.connect(str(ARQUIVO_DB_SENHAS))
        conn.execute("INSERT OR REPLACE INTO senhas VALUES (?,?,?,?)", (bloco, apto, empresa, senha))
        conn.commit(); conn.close()
        messagebox.showinfo("Sucesso", "Dados de senha atualizados!")