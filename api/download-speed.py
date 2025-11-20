import urllib.request
import urllib.parse
import time
import socket
import threading
import os
import sys
import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

class InternetSpeedTest:
    def __init__(self):
        self.download_urls = [
            'https://proof.ovh.net/files/1Mb.dat',  # 1MB from OVH
            'https://proof.ovh.net/files/10Mb.dat', # 10MB from OVH
            'https://speed.cloudflare.com/__down?bytes=1048576',  # 1MB from Cloudflare
            'https://speed.cloudflare.com/__down?bytes=10485760', # 10MB from Cloudflare
            'https://www.speedtest.net/api/download/random/1000x1000.jpg', # ~1MB from Speedtest.net
            'https://github.com/lodash/lodash/archive/refs/heads/main.zip', # Variable size from GitHub
        ]
        
        self.upload_urls = [
            'https://httpbin.org/post',
            'https://postman-echo.com/post',
            'https://requestcatcher.com/test',  # Alternative test endpoint
        ]
        
        self.ping_hosts = [
            ('google.com', 80),
            ('cloudflare.com', 80),
            ('github.com', 80),
            ('microsoft.com', 80),
            ('8.8.8.8', 53),  # Google DNS
        ]
        
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    def measure_ping(self, host_port, timeout=3):
        """Measure ping time to a host with improved error handling"""
        host, port = host_port if isinstance(host_port, tuple) else (host_port, 80)
        
        ping_times = []
        for _ in range(3):  # Average of 3 pings for better accuracy
            try:
                start_time = time.perf_counter()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                sock.close()
                end_time = time.perf_counter()
                
                if result == 0:
                    ping_times.append((end_time - start_time) * 1000)
                    time.sleep(0.1)  # Small delay between pings
                else:
                    continue
            except Exception as e:
                print(f"Ping error to {host}: {e}")
                continue
        
        return statistics.mean(ping_times) if ping_times else None

    def download_speed_test(self, url, timeout=30):
        """Enhanced download speed test with better error handling"""
        try:
            server_name = url.split('/')[2] if '//' in url else 'unknown'
            print(f"Testing download from: {server_name}")
            
            req = urllib.request.Request(url)
            req.add_header('User-Agent', self.user_agent)
            req.add_header('Accept', '*/*')
            req.add_header('Accept-Language', 'en-US,en;q=0.9')
            req.add_header('Accept-Encoding', 'gzip, deflate, br')
            req.add_header('Connection', 'keep-alive')
            req.add_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            req.add_header('Pragma', 'no-cache')
            
            start_time = time.perf_counter()
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                # Progressive chunk reading for better memory management
                chunk_size = 8192
                total_data = 0
                data_chunks = []
                
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    data_chunks.append(chunk)
                    total_data += len(chunk)
                    
                    # Limit total download to avoid excessive data usage
                    if total_data > 50 * 1024 * 1024:  # 50MB max
                        break
                
            end_time = time.perf_counter()
            
            download_time = end_time - start_time
            
            if total_data > 1024 and download_time > 0.1:  # At least 1KB and 0.1 seconds
                speed_bps = total_data / download_time
                speed_mbps = (speed_bps * 8) / (1024 * 1024)
                
                return {
                    'size_mb': total_data / (1024 * 1024),
                    'time_seconds': download_time,
                    'speed_mbps': speed_mbps,
                    'server': server_name,
                    'url': url
                }
            else:
                print(f"Insufficient data: {total_data} bytes in {download_time:.2f}s")
                return None
            
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code} error from {server_name}: {e.reason}")
            return None
        except urllib.error.URLError as e:
            print(f"URL error from {server_name}: {e.reason}")
            return None
        except socket.timeout:
            print(f"Timeout connecting to {server_name}")
            return None
        except Exception as e:
            print(f"Download test failed for {server_name}: {e}")
            return None

    def upload_speed_test(self, size_kb=100, timeout=30):
        """Improved upload speed test with multiple size attempts"""
        test_sizes = [size_kb, size_kb // 2, size_kb * 2]  # Try different sizes
        
        for size in test_sizes:
            for upload_url in self.upload_urls:
                try:
                    server_name = upload_url.split('/')[2]
                    print(f"Testing upload to {server_name} ({size} KB)...")
                    
                    # Create test data
                    test_data = {
                        'test_type': 'speed_test',
                        'timestamp': time.time(),
                        'data': 'A' * (size * 1024),  # Simple repeated data
                        'size_kb': size
                    }
                    
                    post_data = json.dumps(test_data).encode('utf-8')
                    
                    req = urllib.request.Request(upload_url)
                    req.add_header('Content-Type', 'application/json')
                    req.add_header('Content-Length', str(len(post_data)))
                    req.add_header('User-Agent', self.user_agent)
                    req.data = post_data
                    
                    start_time = time.perf_counter()
                    
                    with urllib.request.urlopen(req, timeout=timeout) as response:
                        response.read()  # Read response to complete the request
                        
                    end_time = time.perf_counter()
                    
                    upload_time = end_time - start_time
                    
                    if upload_time > 0.1:  # Minimum time for reliable measurement
                        speed_bps = len(post_data) / upload_time
                        speed_mbps = (speed_bps * 8) / (1024 * 1024)
                        
                        return {
                            'size_mb': len(post_data) / (1024 * 1024),
                            'time_seconds': upload_time,
                            'speed_mbps': speed_mbps,
                            'server': server_name
                        }
                    
                except Exception as e:
                    print(f"Upload test failed for {server_name}: {e}")
                    continue
        
        return None

    def run_parallel_ping_tests(self):
        """Run ping tests in parallel for faster execution"""
        print("Running ping tests...")
        
        with ThreadPoolExecutor(max_workers=len(self.ping_hosts)) as executor:
            future_to_host = {
                executor.submit(self.measure_ping, host): host 
                for host in self.ping_hosts
            }
            
            ping_results = []
            for future in as_completed(future_to_host):
                host = future_to_host[future]
                host_name = host[0] if isinstance(host, tuple) else host
                try:
                    ping_time = future.result(timeout=10)
                    if ping_time is not None:
                        ping_results.append(ping_time)
                        print(f"Ping to {host_name}: {ping_time:.2f} ms")
                    else:
                        print(f"Ping to {host_name}: Failed")
                except Exception as e:
                    print(f"Ping to {host_name}: Error - {e}")
        
        return statistics.mean(ping_results) if ping_results else None

    def run_download_tests(self, max_concurrent=3):
        """Run download tests with limited concurrency"""
        print("\nRunning download tests...")
        download_results = []
        successful_tests = 0
        max_tests = 4  # Limit number of tests
        
        for url in self.download_urls[:max_tests]:
            if successful_tests >= 3:  # Stop after 3 successful tests
                break
                
            result = self.download_speed_test(url)
            if result:
                download_results.append(result['speed_mbps'])
                successful_tests += 1
                print(f"✓ {result['server']}: {result['size_mb']:.2f} MB in {result['time_seconds']:.2f}s = {result['speed_mbps']:.2f} Mbps")
            else:
                print("✗ Test failed")
            
            time.sleep(0.5)  # Small delay between tests
        
        if download_results:
            avg_speed = statistics.mean(download_results)
            max_speed = max(download_results)
            median_speed = statistics.median(download_results)
            
            print(f"\nDownload results:")
            print(f"  Average: {avg_speed:.2f} Mbps")
            print(f"  Median:  {median_speed:.2f} Mbps") 
            print(f"  Peak:    {max_speed:.2f} Mbps")
            
            return median_speed  # Use median as more representative
        return None

    def run_upload_test(self):
        """Run upload test with progressive sizing"""
        print("\nRunning upload test...")
        
        # Try different sizes to find optimal measurement
        test_sizes = [50, 100, 200]  # KB
        best_result = None
        
        for size in test_sizes:
            result = self.upload_speed_test(size)
            if result and result['speed_mbps'] > 0.1:  # Minimum threshold
                print(f"✓ {result['server']}: {result['size_mb']:.3f} MB in {result['time_seconds']:.2f}s = {result['speed_mbps']:.2f} Mbps")
                
                if best_result is None or result['speed_mbps'] > best_result['speed_mbps']:
                    best_result = result
                    
                # If we get a good speed measurement, use it
                if result['speed_mbps'] > 1.0:
                    return result['speed_mbps']
            else:
                print("✗ Upload test failed or too slow")
        
        return best_result['speed_mbps'] if best_result else None

    def estimate_upload_from_download(self, download_speed):
        """Enhanced upload estimation with more connection types"""
        connection_profiles = {
            'satellite': {'ratio': 0.05, 'max_down': 25, 'description': 'Satellite'},
            'dsl': {'ratio': 0.1, 'max_down': 15, 'description': 'DSL'},
            'cable_basic': {'ratio': 0.2, 'max_down': 50, 'description': 'Cable Basic'},
            'cable_premium': {'ratio': 0.3, 'max_down': 200, 'description': 'Cable Premium'},
            'fiber_asymmetric': {'ratio': 0.4, 'max_down': 500, 'description': 'Fiber Asymmetric'},
            'fiber_symmetric': {'ratio': 0.9, 'max_down': float('inf'), 'description': 'Fiber Symmetric'},
        }
        
        # Determine connection type based on download speed
        for conn_type, profile in connection_profiles.items():
            if download_speed <= profile['max_down']:
                estimated_upload = download_speed * profile['ratio']
                return estimated_upload, profile['description']
        
        # Default to symmetric fiber for very high speeds
        return download_speed * 0.9, 'High-Speed Fiber'

    def analyze_connection_quality(self, ping, download, upload):
        """Provide detailed connection analysis"""
        analysis = []
        
        # Ping analysis
        if ping is not None:
            if ping < 10:
                analysis.append("🟢 Excellent latency - Perfect for gaming and real-time apps")
            elif ping < 30:
                analysis.append("🟡 Good latency - Suitable for most online activities")
            elif ping < 100:
                analysis.append("🟠 Fair latency - May notice delays in interactive apps")
            else:
                analysis.append("🔴 High latency - May experience lag in real-time applications")
        
        # Download analysis
        if download is not None:
            if download > 100:
                analysis.append("🟢 Ultra-fast download - 4K streaming, large file transfers")
            elif download > 25:
                analysis.append("🟢 Fast download - HD streaming, video calls, cloud services")
            elif download > 10:
                analysis.append("🟡 Good download - Standard streaming, web browsing")
            elif download > 5:
                analysis.append("🟠 Adequate download - Basic streaming and browsing")
            else:
                analysis.append("🔴 Slow download - Limited multimedia capability")
        
        # Upload analysis
        if upload is not None and upload > 0.5:
            if upload > 10:
                analysis.append("🟢 Fast upload - Video conferencing, content creation")
            elif upload > 5:
                analysis.append("🟡 Good upload - Video calls, file sharing")
            elif upload > 1:
                analysis.append("🟠 Basic upload - Email attachments, light sharing")
            else:
                analysis.append("🔴 Limited upload - Slow file sharing")
        
        return analysis

    def run_full_test(self):
        """Run comprehensive internet speed test"""
        print("=" * 60)
        print("🌐 COMPREHENSIVE INTERNET SPEED TEST")
        print("=" * 60)
        print("Testing multiple servers for accurate measurements...\n")
        
        # Run tests
        avg_ping = self.run_parallel_ping_tests()
        download_speed = self.run_download_tests()
        upload_speed = self.run_upload_test()
        
        # Results section
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS")
        print("=" * 60)
        
        # Display results with quality indicators
        if avg_ping is not None:
            ping_quality = "Excellent" if avg_ping < 20 else "Good" if avg_ping < 50 else "Fair" if avg_ping < 100 else "Poor"
            print(f"📡 Ping (Latency):    {avg_ping:.1f} ms ({ping_quality})")
        else:
            print("📡 Ping (Latency):    Unable to measure")
            
        if download_speed is not None:
            download_quality = "Ultra-Fast" if download_speed > 100 else "Very Fast" if download_speed > 25 else "Fast" if download_speed > 10 else "Moderate" if download_speed > 5 else "Slow"
            print(f"⬇️  Download Speed:    {download_speed:.1f} Mbps ({download_quality})")
        else:
            print("⬇️  Download Speed:    Unable to measure")
            
        if upload_speed is not None and upload_speed > 0.5:
            upload_quality = "Excellent" if upload_speed > 25 else "Good" if upload_speed > 5 else "Fair" if upload_speed > 1 else "Limited"
            print(f"⬆️  Upload Speed:      {upload_speed:.1f} Mbps ({upload_quality})")
        else:
            if download_speed is not None:
                estimated_upload, conn_type = self.estimate_upload_from_download(download_speed)
                print(f"⬆️  Upload Speed:      ~{estimated_upload:.1f} Mbps (estimated - {conn_type})")
            else:
                print("⬆️  Upload Speed:      Unable to measure")
        
        # Connection analysis
        print("\n" + "=" * 60)
        print("🔍 CONNECTION ANALYSIS")
        print("=" * 60)
        
        analysis = self.analyze_connection_quality(avg_ping, download_speed, upload_speed or 0)
        for item in analysis:
            print(f"  {item}")
        
        # Recommendations
        print(f"\n{'📝 USAGE RECOMMENDATIONS'}")
        print("=" * 60)
        
        if download_speed and download_speed > 25:
            print("✅ Excellent for: 4K streaming, video conferencing, cloud gaming")
        elif download_speed and download_speed > 10:
            print("✅ Good for: HD streaming, video calls, online gaming")
        elif download_speed and download_speed > 5:
            print("⚠️  Suitable for: Basic streaming, web browsing, email")
        else:
            print("⚠️  Best for: Light web browsing, email, audio streaming")
            
        print("=" * 60)

def check_internet_connection():
    """Enhanced internet connection check"""
    test_hosts = [
        ("8.8.8.8", 53),      # Google DNS
        ("1.1.1.1", 53),      # Cloudflare DNS  
        ("google.com", 80),   # Google HTTP
    ]
    
    for host, port in test_hosts:
        try:
            socket.create_connection((host, port), timeout=5)
            return True
        except OSError:
            continue
    return False

def main():
    """Main function with enhanced error handling"""
    print("🔍 Checking internet connection...")
    
    if not check_internet_connection():
        print("❌ No internet connection detected!")
        print("Please check your network connection and try again.")
        sys.exit(1)
    
    print("✅ Internet connection detected!")
    print("⚠️  Note: This test will use some data for accurate measurements.\n")
    
    try:
        speed_test = InternetSpeedTest()
        speed_test.run_full_test()
    except KeyboardInterrupt:
        print("\n\n❌ Test interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()