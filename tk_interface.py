import tkinter as tk

from trading_helpers import (
    buy_no,
    sell_no,
    cancel_all_orders,
    get_bid_ask_spread,
    get_open_orders,
    get_positions,
    get_recent_trades,
)


def buy_action():
    market = market_var.get()
    try:
        size = float(buy_size.get())
        distance = int(buy_distance.get())
        resp = buy_no(market=market, x_cents_below_ask=distance, size=size)
        print(resp)
    except Exception as exc:
        print(f"Buy error: {exc}")


def sell_action():
    market = market_var.get()
    try:
        size = float(sell_size.get())
        distance = int(sell_distance.get())
        resp = sell_no(market=market, x_cents_above_bid=distance, size=size)
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

# Controls for info refresh
tk.Label(root, text="History min").grid(row=4, column=0, sticky="e")
history_minutes = tk.Entry(root)
history_minutes.insert(0, "60")
history_minutes.grid(row=4, column=1)

def refresh_info() -> None:
    market = market_var.get()
    info_box.delete("1.0", tk.END)
    if not market:
        return
    try:
        bidask = get_bid_ask_spread(market)
        info_box.insert(tk.END, "Bid/Ask/Spread:\n")
        for outcome, vals in bidask.items():
            info_box.insert(
                tk.END,
                f"{outcome}: bid={vals['bid']} ask={vals['ask']} spread={vals['spread']}\n",
            )

        pos = get_positions(market)
        info_box.insert(tk.END, "\nPositions:\n")
        for outcome, bal in pos.items():
            info_box.insert(tk.END, f"{outcome}: {bal}\n")

        orders = get_open_orders(market)
        info_box.insert(tk.END, "\nOpen orders:\n")
        for o in orders:
            info_box.insert(
                tk.END,
                f"{o.get('side')} {o.get('size')} @ {o.get('price')}\n",
            )

        mins = int(history_minutes.get()) if history_minutes.get() else 60
        trades = get_recent_trades(market, mins)
        info_box.insert(tk.END, f"\nExecuted orders (last {mins} min):\n")
        for t in trades:
            info_box.insert(tk.END, f"{t}\n")
    except Exception as exc:
        info_box.insert(tk.END, f"Error: {exc}\n")

refresh_btn = tk.Button(root, text="Refresh", command=refresh_info)
refresh_btn.grid(row=4, column=2, columnspan=3)

# Info text box
info_box = tk.Text(root, width=80, height=15)
info_box.grid(row=5, column=0, columnspan=5, pady=5)

root.mainloop()
