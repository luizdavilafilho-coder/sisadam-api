import customtkinter as ctk
import sqlite3
import pathlib
from tkinter import messagebox
from datetime import datetime
from PIL import Image
import modulo_dados_prestadores

# Configuração global de aparência
ctk.set_appearance_mode("dark")

# --- INFRAESTRUTURA DE SEGURANÇA ---
PASTA_BASE = pathlib.Path.home() / "Documents" / "SISADAM"
ARQUIVO_DB_PORTAL = PASTA_BASE / "Arquivos_Banco" / "portal_acesso.db"

def inicializar_seguranca():
    (PASTA_BASE / "Arquivos_Banco").mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(ARQUIVO_DB_PORTAL))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS acesso_portal (
            usuario TEXT PRIMARY KEY, 
            senha TEXT, 
            perfil TEXT
        )
    """)
    usuarios_padrao = [
        ('master', 'master2026!', 'MASTER'),
        ('admin', 'admin2026!', 'ADMIN'),
        ('operador', 'vigia123', 'OPERADOR')
    ]
    for u, s, p in usuarios_padrao:
        if not conn.execute("SELECT * FROM acesso_portal WHERE usuario=?", (u,)).fetchone():
            conn.execute("INSERT INTO acesso_portal VALUES (?, ?, ?)", (u, s, p))
    conn.commit()
    conn.close()

def centralizar_janela(janela, largura, altura):
    janela.update_idletasks()
    tela_largura = janela.winfo_screenwidth()
    tela_altura = janela.winfo_screenheight()
    x = (tela_largura // 2) - (largura // 2)
    y = (tela_altura // 2) - (altura // 2)
    janela.geometry(f"{largura}x{altura}+{x}+{y}")

# --- JANELA DE GESTÃO DE USUÁRIOS ---
class JanelaGestaoUsuarios(ctk.CTkToplevel):
    def __init__(self, master, nivel_acesso):
        super().__init__(master)
        self.title("Gestão de Acessos")
        largura, altura = 400, 550
        centralizar_janela(self, largura, altura)
        self.resizable(False, False)
        self.grab_set() 
        self.nivel = nivel_acesso
        
        titulo = "GESTÃO DE OPERADORES" if self.nivel == "MASTER" else "VISUALIZAÇÃO DE USUÁRIOS"
        ctk.CTkLabel(self, text=titulo, font=("Roboto Mono", 16, "bold"), text_color="#F57C00").pack(pady=15)
        
        self.f_cad = ctk.CTkFrame(self)
        self.f_cad.pack(pady=10, padx=20, fill="x")
        
        # Caixas de texto com fundo BRANCO e letra PRETA
        self.en_u = ctk.CTkEntry(self.f_cad, placeholder_text="Novo Usuário", fg_color="white", text_color="black", placeholder_text_color="gray")
        self.en_u.pack(pady=5, padx=10)
        
        self.en_p = ctk.CTkEntry(self.f_cad, placeholder_text="Senha", show="*", fg_color="white", text_color="black", placeholder_text_color="gray")
        self.en_p.pack(pady=5, padx=10)
        
        self.cb_p = ctk.CTkComboBox(self.f_cad, values=["ADMIN", "OPERADOR"], state="readonly")
        self.cb_p.set("OPERADOR"); self.cb_p.pack(pady=5)
        
        ctk.CTkButton(self.f_cad, text="CADASTRAR", fg_color="#F57C00", text_color="black", command=self.add_u).pack(pady=10)
        
        self.opt_u = ctk.CTkOptionMenu(self, values=[], fg_color="#333")
        self.opt_u.pack(pady=10, padx=20, fill="x")
        self.refresh_u()
        ctk.CTkButton(self, text="EXCLUIR SELECIONADO", fg_color="#A30000", command=self.del_u).pack(pady=10)

    def refresh_u(self):
        conn = sqlite3.connect(str(ARQUIVO_DB_PORTAL))
        res = conn.execute("SELECT usuario, perfil FROM acesso_portal").fetchall()
        conn.close()
        lista = [f"{r[0]} ({r[1]})" for r in res]
        self.opt_u.configure(values=lista)
        if lista: self.opt_u.set(lista[0])

    def add_u(self):
        u, p, pf = self.en_u.get().strip().lower(), self.en_p.get().strip(), self.cb_p.get()
        if u and p:
            conn = sqlite3.connect(str(ARQUIVO_DB_PORTAL))
            try:
                conn.execute("INSERT INTO acesso_portal VALUES (?,?,?)", (u, p, pf))
                conn.commit()
                messagebox.showinfo("Sucesso", "Usuário criado.")
            except: messagebox.showwarning("Aviso", "Usuário já existe.")
            conn.close(); self.refresh_u()

    def del_u(self):
        sel = self.opt_u.get().split(" ")[0].lower()
        if sel == "master": return
        conn = sqlite3.connect(str(ARQUIVO_DB_PORTAL))
        conn.execute("DELETE FROM acesso_portal WHERE usuario=?", (sel,))
        conn.commit(); conn.close(); self.refresh_u()

# --- JANELA DE LOGIN ---
class JanelaLogin(ctk.CTkToplevel):
    def __init__(self, master, perfil):
        super().__init__(master)
        self.title("Autenticação SISADAM")
        largura, altura = 450, 420
        centralizar_janela(self, largura, altura)
        self.grab_set(); self.resizable(False, False)
        self.perfil, self.sucesso, self.user_logado = perfil, False, ""
        
        ctk.CTkLabel(self, text=f"ACESSO {perfil}", font=("Roboto Mono", 18, "bold"), text_color="#F57C00").pack(pady=20)
        
        # Caixas de texto com fundo BRANCO e letra PRETA
        self.ent_user = ctk.CTkEntry(self, placeholder_text="Usuário", width=250, fg_color="white", text_color="black", placeholder_text_color="gray")
        self.ent_user.pack(pady=10)
        
        self.ent_pass = ctk.CTkEntry(self, placeholder_text="Senha", show="*", width=250, fg_color="white", text_color="black", placeholder_text_color="gray")
        self.ent_pass.pack(pady=10)
        
        ctk.CTkButton(self, text="ENTRAR", fg_color="#F57C00", text_color="black", font=("Arial", 12, "bold"), command=self.autenticar).pack(pady=25)
        self.bind('<Return>', lambda event: self.autenticar())

    def autenticar(self):
        u, s = self.ent_user.get().strip().lower(), self.ent_pass.get()
        conn = sqlite3.connect(str(ARQUIVO_DB_PORTAL))
        res = conn.execute("SELECT * FROM acesso_portal WHERE usuario=? AND senha=? AND perfil=?", (u, s, self.perfil)).fetchone()
        conn.close()
        if res: self.sucesso, self.user_logado = True, u.upper(); self.destroy()
        else: messagebox.showerror("Erro", "Credenciais inválidas.")

# --- INTERFACE PRINCIPAL ---
class AppSISADAM(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SISADAM - Gestão de Portaria - Versão 3.0")
        self.update() 
        self.after(100, lambda: self.state("zoomed")) 
        self.sessao_ativa = None  
        self.usuario_nome = None
        self.cor_destaque = "#F57C00"
        self.lista_imagens = ["FRENTE-NOVA.png", "FRENTE-02.png", "FRENTE-03.png", "FRENTE-04.png", "FRENTE-05.png", "FRENTE-06.png", "FRENTE-07.png", "FRENTE-08.png", "FRENTE-09.png", "FRENTE-10.png", "frente-11.png", "FRENTE-12.png", "FRENTE-13.png", "FRENTE-14.png", "FRENTE-15.png"]
        self.indice_slide = 0
        self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)
        self.montar_menu_lateral()
        self.frame_main = ctk.CTkFrame(self, fg_color="black")
        self.frame_main.grid(row=0, column=1, sticky="nsew")
        self.frame_main.grid_columnconfigure(0, weight=1); self.frame_main.grid_rowconfigure(0, weight=1)
        self.label_bg = ctk.CTkLabel(self.frame_main, text="")
        self.label_bg.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.rodar_slideshow()
        self.mostrar_bloqueio()
        self.verificar_virada_de_turno()

    def montar_menu_lateral(self):
        self.menu = ctk.CTkFrame(self, width=250, fg_color="#121212", corner_radius=0)
        self.menu.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.menu, text="SISADAM", font=("Impact", 35), text_color=self.cor_destaque).pack(pady=(30, 5))
        ctk.CTkLabel(self.menu, text="SISTEMA DE ADMINISTRAÇÃO\nARACY/MARIANA\nGESTÃO DE PORTARIA", font=("Arial", 10, "bold"), text_color="#FFFFFF", justify="center").pack(pady=(0, 20))
        self.btn_inicio = self.criar_botao("INÍCIO", cmd=self.mostrar_bloqueio)
        self.btn_moradores = self.criar_botao("MORADORES", cmd=self.abrir_moradores)
        self.btn_veiculos_moradores = self.criar_botao("VEÍCULOS MORADORES", cmd=self.abrir_veiculos_moradores)
        self.btn_visitantes = self.criar_botao("VISITANTES", cmd=self.abrir_visitantes)
        self.btn_veiculos_visitantes = self.criar_botao("VEÍCULOS VISITANTES", cmd=self.abrir_veiculos_visitantes)
        self.btn_prestadores = self.criar_botao("PRESTADORES", cmd=self.abrir_prestadores)
        self.btn_entregas = self.criar_botao("ENTREGAS", cmd=self.abrir_entregas)
        self.btn_auditoria = self.criar_botao("AUDITORIA / COFRE", cmd=self.abrir_auditoria)
        self.btn_gestao_user = self.criar_botao("GESTÃO USUÁRIOS", cmd=self.abrir_gestao_usuarios)
        self.rodape = ctk.CTkFrame(self.menu, fg_color="transparent")
        self.rodape.pack(side="bottom", fill="x", pady=20)
        ctk.CTkLabel(self.rodape, text="©2026", font=("Arial", 10), text_color="#FFEE02").pack()
        ctk.CTkLabel(self.rodape, text="Desenvolvido por: \nLuiz S.d'Avila Filho", font=("Arial", 10), text_color="#FFFFFF").pack()
        self.frame_relogio = ctk.CTkFrame(self.menu, fg_color="#1E1E1E", border_width=1, border_color=self.cor_destaque)
        self.frame_relogio.pack(side="bottom", fill="x", padx=15, pady=10)
        self.lbl_data = ctk.CTkLabel(self.frame_relogio, text="", font=("Arial", 11, "bold"), text_color="white"); self.lbl_data.pack()
        self.lbl_hora = ctk.CTkLabel(self.frame_relogio, text="", font=("Roboto Mono", 16, "bold"), text_color=self.cor_destaque); self.lbl_hora.pack()
        self.atualizar_relogio()

    def atualizar_relogio(self):
        agora = datetime.now()
        self.lbl_data.configure(text=agora.strftime("%d/%m/%Y"))
        self.lbl_hora.configure(text=agora.strftime("%H:%M:%S"))
        self.after(1000, self.atualizar_relogio)

    def rodar_slideshow(self):
        try:
            largura, altura = self.frame_main.winfo_width(), self.frame_main.winfo_height()
            if largura < 10: largura, altura = 900, 750
            img = Image.open(self.lista_imagens[self.indice_slide])
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(largura, altura))
            self.label_bg.configure(image=ctk_img)
            self.indice_slide = (self.indice_slide + 1) % len(self.lista_imagens)
        except: pass
        self.after(5000, self.rodar_slideshow)

    def criar_botao(self, texto, cmd=None):
        btn = ctk.CTkButton(self.menu, text=texto, state="disabled", fg_color="#333", font=("Roboto Mono", 12, "bold"), command=cmd)
        btn.pack(pady=5, padx=20, fill="x")
        return btn

    def mostrar_bloqueio(self):
        self.limpar_tela_principal()
        f_box = ctk.CTkFrame(self.frame_main, fg_color="#9C2222", border_width=2, border_color=self.cor_destaque)
        f_box.place(relx=0.5, rely=0.5, anchor="center")
        if not self.sessao_ativa:
            ctk.CTkLabel(f_box, text="SISTEMA BLOQUEADO", font=("Arial", 16, "bold"), text_color="#fffb00").pack(pady=20, padx=40)
            for p in ["OPERADOR", "ADMIN", "MASTER"]:
                ctk.CTkButton(f_box, text=f"LOGIN {p}", command=lambda pref=p: self.abrir_login(pref)).pack(pady=5)
        else:
            ctk.CTkLabel(f_box, text=f"SESSÃO ATIVA: {self.sessao_ativa}", text_color="#fffb00").pack(pady=20, padx=40)
            ctk.CTkButton(f_box, text="SAIR DO SISTEMA", fg_color="#A30000", command=self.logout).pack(pady=10)

    def abrir_login(self, perfil):
        jan = JanelaLogin(self, perfil)
        self.wait_window(jan)
        if jan.sucesso:
            self.sessao_ativa = perfil
            self.usuario_nome = jan.user_logado
            self.configurar_permissoes()
            self.mostrar_bloqueio()

    def limpar_tela_principal(self):
        for widget in self.frame_main.winfo_children():
            if widget != self.label_bg: widget.destroy()

    def abrir_gestao_usuarios(self):
        JanelaGestaoUsuarios(self, self.sessao_ativa)

    def abrir_moradores(self):
        self.limpar_tela_principal()
        try:
            import modulo_dados_moradores
            self.tela_atual = modulo_dados_moradores.BancoMoradores(self.frame_main, nivel=self.sessao_ativa)
            self.tela_atual.place(relx=0, rely=0, relwidth=1, relheight=1)
        except Exception as e:
            # Isso aqui vai abrir uma janela te dizendo o erro real (ex: falta de coluna, erro de vírgula, etc)
            messagebox.showerror("Erro no Módulo Moradores", f"Falha ao carregar o seu módulo: {e}")

    def abrir_veiculos_moradores(self):
        self.limpar_tela_principal()
        try:
            import modulo_veiculos_moradores
            tela = modulo_veiculos_moradores.BancoVeiculosMoradores(self.frame_main, nivel=self.sessao_ativa)
            tela.place(relx=0, rely=0, relwidth=1, relheight=1)
        except: pass

    def abrir_visitantes(self):
        self.limpar_tela_principal()
        try:
            import modulo_dados_visitantes
            tela = modulo_dados_visitantes.BancoVisitantes(self.frame_main, nivel=self.sessao_ativa)
            tela.place(relx=0, rely=0, relwidth=1, relheight=1)
        except: pass

    def abrir_veiculos_visitantes(self):
        self.limpar_tela_principal()
        try:
            import modulo_veiculos_visitantes
            tela = modulo_veiculos_visitantes.BancoVeiculosVisitantes(self.frame_main, nivel=self.sessao_ativa)
            tela.place(relx=0, rely=0, relwidth=1, relheight=1)
        except: pass

    def abrir_entregas(self):
        self.limpar_tela_principal()
        try:
            import modulo_dados_entregas
            self.tela_atual = modulo_dados_entregas.BancoEntregas(self.frame_main, nivel=self.sessao_ativa)
            self.tela_atual.place(relx=0, rely=0, relwidth=1, relheight=1)
        except Exception as e:
            # Isso vai forçar o Windows a mostrar o erro real na tela
            messagebox.showerror("Erro no Módulo Entregas", f"Falha ao carregar o módulo: {e}")

    def abrir_prestadores(self):
        self.limpar_tela_principal()
        try:
            # Note o uso de self.usuario_nome (que é a variável que você já tem no main)
            self.tela_atual = modulo_dados_prestadores.BancoPrestadores(
                self.frame_main, 
                nivel=self.sessao_ativa, 
                usuario=self.usuario_nome
            )
            self.tela_atual.place(relx=0, rely=0, relwidth=1, relheight=1)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha: {e}")

    def abrir_auditoria(self):
        self.limpar_tela_principal()
        try:
            import modulo_cofre
            tela = modulo_cofre.Cofre(self.frame_main, nivel=self.sessao_ativa)
            tela.place(relx=0, rely=0, relwidth=1, relheight=1)
        except: pass

    def configurar_permissoes(self):
        btns = [self.btn_inicio, self.btn_moradores, self.btn_veiculos_moradores, self.btn_visitantes, self.btn_veiculos_visitantes, self.btn_prestadores, self.btn_entregas]
        for b in btns: b.configure(state="normal", fg_color=self.cor_destaque, text_color="black")
        if self.sessao_ativa in ["ADMIN", "MASTER"]:
            self.btn_auditoria.configure(state="normal", fg_color="#44A5FF")
            self.btn_gestao_user.configure(state="normal", fg_color=self.cor_destaque)

    def logout(self):
        self.sessao_ativa = self.usuario_nome = None
        for b in self.menu.winfo_children():
            if isinstance(b, ctk.CTkButton): b.configure(state="disabled", fg_color="#333")
        self.mostrar_bloqueio()

    def verificar_virada_de_turno(self):
        """Monitor invisível: checa se o dia mudou para disparar o backup"""
        from datetime import datetime
        import json
        
        agora = datetime.now()
        data_hoje = agora.strftime('%Y-%m-%d')
        path_backup = pathlib.Path.home() / "Documents" / "SISADAM" / "Arquivos_Banco" / "ultimo_backup.json"
        
        ultimo_backup = ""
        if path_backup.exists():
            try:
                with open(path_backup, 'r') as f:
                    ultimo_backup = json.load(f).get("data", "")
            except: pass

        # Se o dia atual for diferente do último registrado, executa o backup
        if data_hoje != ultimo_backup:
            # Chama o fechamento no módulo que estiver carregado na tela
            if hasattr(self, 'modulo_ativo') and self.modulo_ativo:
                if hasattr(self.modulo_ativo, 'fechar_ciclo_diario'):
                    self.modulo_ativo.fechar_ciclo_diario()
            
            # Atualiza a data do último backup
            path_backup.parent.mkdir(parents=True, exist_ok=True)
            with open(path_backup, 'w') as f:
                json.dump({"data": data_hoje}, f)
        
        # Verifica novamente em 60 segundos
        self.after(60000, self.verificar_virada_de_turno)

if __name__ == "__main__":
    inicializar_seguranca()
    app = AppSISADAM()
    app.mainloop()