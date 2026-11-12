import streamlit as st
import json
import os

STOCK_FILE = "shop_stock.json"
KHATA_FILE = "customer_khata.json"

def load_data(file_name):
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_data(file_name, data):
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

st.title("🛒 مفید اور آسان دکان مینجمنٹ سسٹم (POS)")

choice = st.sidebar.radio(
    "براہ کرم اپنا حصہ منتخب کریں:",
    [
        "1. اسٹاک اور پروڈکٹ مینجمنٹ",
        "2. بلنگ اور سیلز سسٹم",
        "3. ادھار کھاتہ سسٹم"
    ]
)

# --- حصہ 1: اسٹاک مینجمنٹ ---
if choice == "1. اسٹاک اور پروڈکٹ مینجمنٹ":
    st.header("📦 اسٹاک اور پروڈکٹ مینجمنٹ")
    stock = load_data(STOCK_FILE)
    
    st.subheader("نئی چیز (پروڈکٹ) شامل کریں")
    name = st.text_input("چیز کا نام لکھیں (مثلاً DAP Khad):")
    price = st.number_input("فی یونٹ قیمت (روپے میں):", min_value=0.0, step=10.0)
    qty = st.number_input("موجودہ مقدار (تعداد/بوری):", min_value=0, step=1)
    
    if st.button("اسٹاک میں محفوظ کریں"):
        if name.strip():
            stock[name.strip()] = {"price": price, "quantity": qty}
            save_data(STOCK_FILE, stock)
            st.success(f"کامیابی! '{name}' کو اسٹاک میں محفوظ کر دیا گیا ہے۔")
        else:
            st.error("نام خالی نہیں ہو سکتا!")

    st.divider()
    st.subheader("موجودہ اسٹاک کی فہرست")
    if stock:
        stock_list = [{"پروڈکٹ کا نام": k, "قیمت (روپے)": v["price"], "موجود مقدار": v["quantity"]} for k, v in stock.items()]
        st.table(stock_list)
    else:
        st.info("فی الحال اسٹاک خالی ہے۔ اوپر سے کوئی چیز شامل کریں۔")

# --- حصہ 2: بلنگ سسٹم ---
elif choice == "2. بلنگ اور سیلز سسٹم":
    st.header("🧾 بلنگ اور سیلز سسٹم")
    stock = load_data(STOCK_FILE)
    
    if not stock:
        st.warning("اسٹاک خالی ہے! پہلے اسٹاک میں چیزیں شامل کریں۔")
    else:
        if "cart" not in st.session_state:
            st.session_state.cart = []

        item_name = st.selectbox("فروخت ہونے والی چیز منتخب کریں:", list(stock.keys()))
        available_qty = stock[item_name]["quantity"]
        item_price = stock[item_name]["price"]
        st.write(f"فی یونٹ قیمت: **{item_price} روپے** | اسٹاک میں موجود: **{available_qty}**")
        
        sell_qty = st.number_input("فروخت کی تعداد درج کریں:", min_value=1, max_value=max(1, available_qty), step=1)
        
        if st.button("بل (Cart) میں شامل کریں"):
            if available_qty >= sell_qty:
                total = item_price * sell_qty
                st.session_state.cart.append({"پروڈکٹ": item_name, "تعداد": sell_qty, "قیمت": item_price, "کل رقم": total})
                stock[item_name]["quantity"] -= sell_qty
                save_data(STOCK_FILE, stock)
                st.success(f"'{item_name}' بل میں شامل ہو گیا اور اسٹاک اپ ڈیٹ ہو گیا!")
                st.rerun()
            else:
                st.error("اسٹاک میں اتنی مقدار موجود نہیں!")

        if st.session_state.cart:
            st.divider()
            st.subheader("📄 موجودہ بل (Receipt)")
            st.table(st.session_state.cart)
            grand_total = sum(item["کل رقم"] for item in st.session_state.cart)
            st.subheader(f"کل قابلِ ادائیگی رقم: {grand_total} روپے")
            
            if st.button("نیا بل شروع کریں (پرانا صاف کریں)"):
                st.session_state.cart = []
                st.rerun()

# --- حصہ 3: ادھار کھاتہ سسٹم ---
elif choice == "3. ادھار کھاتہ سسٹم":
    st.header("📒 ادھار کھاتہ سسٹم (Khata)")
    khata = load_data(KHATA_FILE)
    
    tab1, tab2 = st.tabs(["نیا ادھار / وصولی درج کریں", "تمام گاہکوں کا کھاتہ دیکھیں"])
    
    with tab1:
        cust_name = st.text_input("گاہک کا نام لکھیں:")
        action = st.radio("عمل منتخب کریں:", ["نیا ادھار ڈالیں (+)", "ادھار وصول کریں (-)"])
        amount = st.number_input("رقم درج کریں (روپے):", min_value=0.0, step=100.0)
        
        if st.button("کھاتہ اپ ڈیٹ کریں"):
            if cust_name.strip() and amount > 0:
                c_name = cust_name.strip()
                current_bal = khata.get(c_name, 0.0)
                if action == "نیا ادھار ڈالیں (+)":
                    khata[c_name] = current_bal + amount
                    st.success(f"{c_name} کے کھاتے میں {amount} روپے ادھار درج ہو گئے۔ کل بقایا: {khata[c_name]}")
                else:
                    khata[c_name] = max(0.0, current_bal - amount)
                    st.success(f"{c_name} سے {amount} روپے وصول ہو گئے۔ بقایا رقم: {khata[c_name]}")
                save_data(KHATA_FILE, khata)
            else:
                st.error("براہ کرم گاہک کا نام اور درست رقم درج کریں۔")
                
    with tab2:
        if khata:
            khata_list = [{"گاہک کا نام": k, "بقایا ادھار (روپے)": v} for k, v in khata.items()]
            st.table(khata_list)
        else:
            st.info("فی الحال کوئی ادھار کھاتہ موجود نہیں۔")
