import speedtest
speed = speedtest.Speedtest()
print("Download Speed:", speed.download() / 1_000_000, "Mbps")
print("Upload Speed:", speed.upload() / 1_000_000, "Mbps")
print("Ping:", speed.results.ping, "ms")