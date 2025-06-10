import tkinter as tk
from market_prices import buyNo, sellNo, cancel_all_orders


def buy_action():
    market = market_var.get()
    try:
        size = float(buy_size.get())
        distance = int(buy_distance.get())
        resp = buyNo(market=market, x_cents_below_ask=distance, size=size)
        print(resp)
    except Exception as exc:
        print(f"Buy error: {exc}")


def sell_action():
    market = market_var.get()
    try:
        size = float(sell_size.get())
        distance = int(sell_distance.get())
        resp = sellNo(market=market, x_cents_above_bid=distance, size=size)
        print(resp)
    except Exception as exc:
        print(f"Sell error: {exc}")


def cancel_action():
    resp = cancel_all_orders()
    print(resp)


root = tk.Tk()
root.title("Polymarket Interface")

# Market input
tk.Label(root, text="Market ID or slug").grid(row=0, column=0, sticky="e")
market_var = tk.StringVar()
market_entry = tk.Entry(root, textvariable=market_var)
market_entry.grid(row=0, column=1, columnspan=3, sticky="we")

# BuyNo controls
tk.Label(root, text="Buy size").grid(row=1, column=0, sticky="e")
buy_size = tk.Entry(root)
buy_size.insert(0, "1")
buy_size.grid(row=1, column=1)

tk.Label(root, text="¢ below ask").grid(row=1, column=2, sticky="e")
buy_distance = tk.Entry(root)
buy_distance.insert(0, "1")
buy_distance.grid(row=1, column=3)

tk.Button(root, text="BuyNo", command=buy_action).grid(row=1, column=4)

# SellNo controls
tk.Label(root, text="Sell size").grid(row=2, column=0, sticky="e")
sell_size = tk.Entry(root)
sell_size.insert(0, "1")
sell_size.grid(row=2, column=1)

tk.Label(root, text="¢ above bid").grid(row=2, column=2, sticky="e")
sell_distance = tk.Entry(root)
sell_distance.insert(0, "1")
sell_distance.grid(row=2, column=3)

tk.Button(root, text="SellNo", command=sell_action).grid(row=2, column=4)

# Cancel button
cancel_btn = tk.Button(root, text="Cancel all orders", command=cancel_action)
cancel_btn.grid(row=3, column=0, columnspan=5, pady=5)

root.mainloop()
