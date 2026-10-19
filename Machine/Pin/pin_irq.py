from machine import Pin


def irq_handler(pin):
    print("irq_handler called")


def main():
    p000 = Pin("P000")
    p000_irq = p000.irq(irq_handler)

    p001 = Pin("P001")
    p001_irq = p001.irq(irq_handler)


if __name__ == '__main__':
    main()
