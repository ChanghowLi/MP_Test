from machine import I2C


MAG_ADDR = 0x30
MAG_ID_REG = 0x39
MAG_ID_EXPECT = 0x10

IMU_ADDR = 0x68
IMU_ID_REG = 0x75
IMU_ID_EXPECT = 0x67

TEST_COUNT = 10

i2c = I2C(0)

print("I2C devices:", [hex(x) for x in i2c.scan()])

fail = 0

for i in range(TEST_COUNT):
    mag_id = i2c.readfrom_mem(MAG_ADDR, MAG_ID_REG, 1)[0]
    imu_id = i2c.readfrom_mem(IMU_ADDR, IMU_ID_REG, 1)[0]

    if mag_id != MAG_ID_EXPECT or imu_id != IMU_ID_EXPECT:
        fail += 1
        print(i, "FAIL", hex(mag_id), hex(imu_id))

print("MMC5603NJ ID:", hex(mag_id))
print("ICM-42670-P ID:", hex(imu_id))

if fail == 0:
    print("Sensor ID test: PASS")
else:
    print("Sensor ID test: FAIL", fail, "/", TEST_COUNT)
