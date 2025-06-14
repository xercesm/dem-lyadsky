import tkinter as tk
from tkinter import ttk, messagebox
import pymysql
from PIL import Image, ImageTk


class PartnerRequestsRepository:
    def __init__(self, host, user, password, database, port=3306):
        self.connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            cursorclass=pymysql.cursors.DictCursor,
            charset='utf8mb4'
        )

    def get_all_requests_with_partner_info(self):
        query = """
        SELECT 
            pr.request_id,
            pr.quantity,
            p.min_price,
            p.product_name,
            par.partner_id,
            par.partner_name,
            par.director_name,
            par.legal_address,
            par.phone,
            par.rating,
            par.partner_type_id,
            pr.product_id
        FROM partner_product_requests pr
        JOIN products p ON pr.product_id = p.product_id
        JOIN partners par ON pr.partner_id = par.partner_id
        ORDER BY pr.request_id ASC;
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
        return results

    def get_products(self):
        query = "SELECT product_id, product_name FROM products ORDER BY product_id ASC"
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def get_partners(self):
        query = "SELECT partner_id, partner_name, partner_type_id FROM partners ORDER BY partner_id ASC"
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def create_partner(self, partner_type_id, partner_name, director_name, legal_address, phone, email, inn, rating):
        query = """
        INSERT INTO partners (
            partner_type_id, 
            partner_name, 
            director_name, 
            legal_address, 
            phone,
            email,
            inn,
            rating
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (partner_type_id, partner_name, director_name, legal_address, phone, email, inn, rating))
            self.connection.commit()
            return cursor.lastrowid

    def create_request(self, product_id, partner_id, quantity):
        query = "INSERT INTO partner_product_requests (product_id, partner_id, quantity) VALUES (%s, %s, %s)"
        with self.connection.cursor() as cursor:
            cursor.execute(query, (product_id, partner_id, quantity))
            self.connection.commit()

    def update_request(self, request_id, product_id, partner_id, quantity):
        query = "UPDATE partner_product_requests SET product_id=%s, partner_id=%s, quantity=%s WHERE request_id=%s"
        with self.connection.cursor() as cursor:
            cursor.execute(query, (product_id, partner_id, quantity, request_id))
            self.connection.commit()

    def delete_request(self, request_id):
        query = "DELETE FROM partner_product_requests WHERE request_id=%s"
        with self.connection.cursor() as cursor:
            cursor.execute(query, (request_id,))
            self.connection.commit()

    def close(self):
        self.connection.close()


class PartnerRequestsApp(tk.Tk):
    def __init__(self, repo: PartnerRequestsRepository):
        super().__init__()
        self.title("Список заявок партнеров")
        self.geometry("480x700")
        self.resizable(False, False)
        self.repo = repo
        self.configure(bg="#FFFFFF")

        try:
            self.iconbitmap("icon.ico")
        except Exception:
            pass

        self.partner_type_names = {
            1: "ЗАО",
            2: "ООО",
            3: "ПАО",
            4: "ОАО"
        }

        style = ttk.Style(self)
        style.theme_use('default')

        style.configure('Header.TFrame', background='#BBDCFA')
        style.configure('Header.TLabel', background='#BBDCFA', foreground='#0C4882',
                        font=("Bahnschrift Light SemiCondensed", 16, 'bold'))
        style.configure('Accent.TButton', foreground='white', background='#0C4882')
        style.map('Accent.TButton',
                  background=[('active', '#06436a'), ('!active', '#0C4882')],
                  foreground=[('active', 'white'), ('!active', 'white')])
        style.configure('Card.TFrame', background='#FFFFFF')
        style.configure('Card.TLabel', background='#FFFFFF', font=("Bahnschrift Light SemiCondensed", 10, 'bold'))
        style.configure('CardValue.TLabel', background='#FFFFFF')

        header_frame = ttk.Frame(self, style='Header.TFrame', padding=10)
        header_frame.pack(fill=tk.X)

        try:
            logo_image = Image.open("logo.png")
            logo_image = logo_image.resize((100, 50), Image.LANCZOS)
            self.logo = ImageTk.PhotoImage(logo_image)
            logo_label = ttk.Label(header_frame, image=self.logo, style='Header.TLabel')
            logo_label.pack(side=tk.LEFT, padx=10)
        except Exception:
            pass

        title_label = ttk.Label(header_frame, text="Список заявок партнеров", style='Header.TLabel')
        title_label.pack(side=tk.LEFT, padx=10)

        btn_frame = ttk.Frame(self, padding=10, style='Card.TFrame')
        btn_frame.pack(fill=tk.X)

        add_request_btn = ttk.Button(btn_frame, text="Создать заявку",
                             command=self.open_create_request_window,
                             style='Accent.TButton')
        add_request_btn.pack(side=tk.LEFT, padx=10)

        add_partner_btn = ttk.Button(btn_frame, text="Создать партнера",
                             command=self.open_create_partner_window,
                             style='Accent.TButton')
        add_partner_btn.pack(side=tk.LEFT, padx=10)

        container = tk.Frame(self, bg="#FFFFFF")
        container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(container, bg="#FFFFFF", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, style='Card.TFrame')
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.request_cards = {}
        self.load_requests()

    def load_requests(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.request_cards.clear()
        requests = self.repo.get_all_requests_with_partner_info()
        for req in requests:
            self.create_request_card(req)

    def create_request_card(self, req):
        frame = ttk.Frame(self.scrollable_frame, relief="solid", borderwidth=1, style='Card.TFrame')
        frame.pack(fill=tk.X, padx=10, pady=8)
        self.request_cards[req['request_id']] = frame

        partner_type_id = req.get('partner_type_id', None)
        partner_name = req['partner_name'] or 'N/A'
        legal_address = req['legal_address'] or 'N/A'
        phone = req['phone'] or 'N/A'
        rating = req['rating'] or 0
        quantity = req['quantity'] or 0
        min_price = float(req['min_price'] or 0.0)
        total_cost = quantity * min_price

        # Получаем название типа партнера
        partner_type = self.partner_type_names.get(partner_type_id, 'N/A')

        lbl_style = 'Card.TLabel'

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Посмотреть продукт",
                         command=lambda rid=req['request_id']: self.show_product_info(rid))
        menu.add_command(label="Редактировать",
                         command=lambda rid=req['request_id']: self.open_edit_request_window(rid))
        menu.add_command(label="Удалить", command=lambda rid=req['request_id']: self.delete_request(rid))

        def on_right_click(event):
            menu.tk_popup(event.x_root, event.y_root)

        frame.bind("<Button-3>", on_right_click)
        frame.bind("<ButtonRelease-3>", lambda e: menu.grab_release())

        top_frame = ttk.Frame(frame, style='Card.TFrame')
        top_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=2)
        top_frame.columnconfigure(1, weight=1)

        type_label = ttk.Label(top_frame, text=f"Тип: {partner_type}", style=lbl_style)
        type_label.grid(row=0, column=0, sticky=tk.W)

        partner_label = ttk.Label(top_frame, text=partner_name, style=lbl_style, anchor='w')
        partner_label.grid(row=0, column=1, sticky="ew", padx=10)

        cost_label = ttk.Label(top_frame, text=f"{total_cost:,.2f}", style=lbl_style, anchor='e')
        cost_label.grid(row=0, column=2, sticky=tk.E)

        ttk.Label(frame, text=legal_address, style=lbl_style).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(frame, text="+7 " + phone, style=lbl_style).grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(frame, text=f"Рейтинг: {rating}", style=lbl_style).grid(row=5, column=0, sticky=tk.W, padx=5,
                                                                              pady=2)

    def show_product_info(self, request_id):
        req = next((r for r in self.repo.get_all_requests_with_partner_info() if r['request_id'] == request_id), None)
        if not req:
            messagebox.showerror("Ошибка", "Заявка не найдена")
            return
        info = f"Наименование продукта: {req['product_name']}\nМинимальная стоимость для партнера: {req['min_price']:,.2f} руб\nКоличество в заявке: {req['quantity']}"
        messagebox.showinfo("Информация о продукте заявки", info)

    def open_create_request_window(self):
        RequestEditWindow(self, self.repo, None, self.reload_data)

    def open_edit_request_window(self, request_id):
        RequestEditWindow(self, self.repo, request_id, self.reload_data)

    def open_create_partner_window(self):
        PartnerCreateWindow(self, self.repo, self.reload_data)

    def reload_data(self):
        self.load_requests()

    def delete_request(self, request_id):
        if messagebox.askyesno("Удаление", "Вы действительно хотите удалить эту заявку?"):
            self.repo.delete_request(request_id)
            self.reload_data()


class RequestEditWindow(tk.Toplevel):
    def __init__(self, parent, repo, request_id, reload_callback):
        super().__init__(parent)
        self.repo = repo
        self.request_id = request_id
        self.reload_callback = reload_callback
        self.title("Редактировать заявку" if request_id else "Создать заявку")
        self.geometry("400x380")
        self.resizable(False, False)

        self.products = self.repo.get_products()
        self.partners = self.repo.get_partners()

        ttk.Label(self, text="Продукт:", font=("Bahnschrift Light SemiCondensed", 10)).pack(pady=6)
        self.product_var = tk.StringVar()
        self.product_combo = ttk.Combobox(self, textvariable=self.product_var, state="readonly", width=50)
        self.product_combo['values'] = [f"{p['product_id']} - {p['product_name']}" for p in self.products]
        self.product_combo.pack()

        ttk.Label(self, text="Партнер:", font=("Bahnschrift Light SemiCondensed", 10)).pack(pady=6)
        self.partner_var = tk.StringVar()
        self.partner_combo = ttk.Combobox(self, textvariable=self.partner_var, state="readonly", width=50)
        self.partner_combo['values'] = [f"{p['partner_id']} - {p['partner_name']}" for p in self.partners]
        self.partner_combo.pack()

        ttk.Label(self, text="Количество:", font=("Bahnschrift Light SemiCondensed", 10)).pack(pady=6)
        self.quantity_var = tk.StringVar()
        self.quantity_entry = ttk.Entry(self, textvariable=self.quantity_var)
        self.quantity_entry.pack()

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=15)

        btn_save = ttk.Button(btn_frame, text="Сохранить", command=self.save_request)
        btn_save.pack(side=tk.LEFT, padx=10)

        btn_cancel = ttk.Button(btn_frame, text="Отмена", command=self.destroy)
        btn_cancel.pack(side=tk.LEFT)

        if self.request_id:
            self.load_request_data()

    def load_request_data(self):
        query = """
        SELECT product_id, partner_id, quantity 
        FROM partner_product_requests WHERE request_id = %s
        """
        with self.repo.connection.cursor() as cursor:
            cursor.execute(query, (self.request_id,))
            data = cursor.fetchone()
        if data:
            product_str = next((f"{p['product_id']} - {p['product_name']}" for p in self.products if p['product_id'] == data['product_id']), "")
            partner_str = next((f"{p['partner_id']} - {p['partner_name']}" for p in self.partners if p['partner_id'] == data['partner_id']), "")
            self.product_var.set(product_str)
            self.partner_var.set(partner_str)
            self.quantity_var.set(str(data['quantity']))

    def save_request(self):
        try:
            quantity = int(self.quantity_var.get())
            if quantity <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректное положительное число для количества.")
            return
        if not self.product_var.get() or not self.partner_var.get():
            messagebox.showerror("Ошибка", "Выберите продукт и партнера.")
            return
        product_id = int(self.product_var.get().split(" - ")[0])
        partner_id = int(self.partner_var.get().split(" - ")[0])

        if self.request_id:
            self.repo.update_request(self.request_id, product_id, partner_id, quantity)
        else:
            self.repo.create_request(product_id, partner_id, quantity)
        self.reload_callback()
        self.destroy()


class PartnerCreateWindow(tk.Toplevel):
    def __init__(self, parent, repo, reload_callback):
        super().__init__(parent)
        self.repo = repo
        self.reload_callback = reload_callback
        self.title("Создать партнера")
        self.geometry("400x600")
        self.resizable(False, False)

        ttk.Label(self, text="Тип партнера:", font=("Bahnschrift Light SemiCondensed", 10)).pack(pady=6)
        self.partner_type_var = tk.StringVar()
        self.partner_type_combo = ttk.Combobox(self, textvariable=self.partner_type_var, state="readonly", width=50)
        self.partner_type_combo['values'] = ['1 - ЗАО', '2 - ООО', '3 - ПАО', '4 - ОАО']
        self.partner_type_combo.pack()

        ttk.Label(self, text="Название партнера:", font=("Bahnschrift Light SemiCondensed", 10)).pack(pady=6)
        self.partner_name_var = tk.StringVar()
        self.partner_name_entry = ttk.Entry(self, textvariable=self.partner_name_var)
        self.partner_name_entry.pack()

        ttk.Label(self, text="ФИО директора:", font=("Bahnschrift Light SemiCondensed", 10)).pack(pady=6)
        self.director_name_var = tk.StringVar()
        self.director_name_entry = ttk.Entry(self, textvariable=self.director_name_var)
        self.director_name_entry.pack()

        ttk.Label(self, text="Юридический адрес:", font=("Bahnschrift Light SemiCondensed", 10)).pack(pady=6)
        self.legal_address_var = tk.StringVar()
        self.legal_address_entry = ttk.Entry(self, textvariable=self.legal_address_var)
        self.legal_address_entry.pack()

        ttk.Label(self, text="Телефон:", font=("Bahnschrift Light SemiCondensed", 10)).pack(pady=6)
        self.phone_var = tk.StringVar()
        self.phone_entry = ttk.Entry(self, textvariable=self.phone_var)
        self.phone_entry.pack()

        ttk.Label(self, text="Email:", font=("Bahnschrift Light SemiCondensed", 10)).pack(pady=6)
        self.email_var = tk.StringVar()
        self.email_entry = ttk.Entry(self, textvariable=self.email_var)
        self.email_entry.pack()

        ttk.Label(self, text="ИНН:", font=("Bahnschrift Light SemiCondensed", 10)).pack(pady=6)
        self.inn_var = tk.StringVar()
        self.inn_entry = ttk.Entry(self, textvariable=self.inn_var)
        self.inn_entry.pack()

        ttk.Label(self, text="Рейтинг:", font=("Bahnschrift Light SemiCondensed", 10)).pack(pady=6)
        self.rating_var = tk.StringVar()
        self.rating_entry = ttk.Entry(self, textvariable=self.rating_var)
        self.rating_entry.pack()

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=15)

        btn_save = ttk.Button(btn_frame, text="Сохранить", command=self.save_partner)
        btn_save.pack(side=tk.LEFT, padx=10)

        btn_cancel = ttk.Button(btn_frame, text="Отмена", command=self.destroy)
        btn_cancel.pack(side=tk.LEFT)

    def save_partner(self):
        if not (self.partner_type_var.get() and self.partner_name_var.get().strip() and self.director_name_var.get().strip()):
            messagebox.showerror("Ошибка", "Заполните обязательные поля: тип, название и ФИО директора.")
            return

        try:
            rating = int(self.rating_var.get()) if self.rating_var.get().strip() else None
        except ValueError:
            messagebox.showerror("Ошибка", "Рейтинг должен быть числом.")
            return

        partner_type_id = int(self.partner_type_var.get().split(' - ')[0])
        partner_name = self.partner_name_var.get().strip()
        director_name = self.director_name_var.get().strip()
        legal_address = self.legal_address_var.get().strip()
        phone = self.phone_var.get().strip()
        email = self.email_var.get().strip() or None
        inn = self.inn_var.get().strip() or None

        self.repo.create_partner(partner_type_id, partner_name, director_name, legal_address, phone, email, inn, rating)
        messagebox.showinfo("Успешно", "Партнер создан")
        self.reload_callback()
        self.destroy()


if __name__ == '__main__':
    repo = PartnerRequestsRepository(
        host='localhost',
        user='root',
        password='toor',
        database='zafir'
    )
    app = PartnerRequestsApp(repo)
    app.mainloop()
    repo.close()

