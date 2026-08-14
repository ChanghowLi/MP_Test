import machine


reson_str = {
    0: "Soft Reset",
    1: "Power ON",
    2: "Hard Reset",
    3: "WDT Reset",
    4: "Deepsleep Reset"
}


if __name__ == "__main__":
    r = machine.reset_cause()
    print("Reset cause: ", reson_str[r])
