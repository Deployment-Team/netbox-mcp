#!/usr/bin/env python3
"""
NetBox MCP Interactive Automation Script

Dit script gebruikt Claude Code om NetBox MCP taken uit te voeren zonder Bridget persona.
Het biedt een interactieve menu voor verschillende NetBox operaties.
"""

import subprocess
import sys
import json
from typing import Optional, List, Dict, Any


class NetBoxMCPAutomation:
    """
    Interactive automation class voor NetBox MCP operaties via Claude Code
    """
    
    def __init__(self):
        self.claude_command = "claude"
        self.mcp_enabled = True
        
    def run_claude_command(self, prompt: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Voer Claude Code uit met gegeven prompt
        
        Args:
            prompt: De instructie voor Claude Code
            timeout: Timeout in seconden
            
        Returns:
            Dict met success status en output
        """
        try:
            print(f"🔄 Executing: {prompt}")
            
            cmd = [self.claude_command, "--prompt", prompt]
            if self.mcp_enabled:
                cmd.append("--mcp-enabled")
                
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "output": result.stdout,
                    "error": result.stderr
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": f"Command timed out after {timeout} seconds"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "output": "",
                "error": "Claude Code not found. Make sure it's installed and in PATH."
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e)
            }
    
    def print_result(self, result: Dict[str, Any], show_full_output: bool = True):
        """Print result van Claude Code operatie"""
        if result["success"]:
            print("✅ Success!")
            if show_full_output and result["output"]:
                print(f"\nOutput:\n{result['output']}")
        else:
            print("❌ Error!")
            if result["error"]:
                print(f"Error: {result['error']}")
            if result["output"]:
                print(f"Output: {result['output']}")
        print("-" * 60)
    
    def system_health_check(self):
        """Check NetBox system health"""
        print("\n🏥 NetBox System Health Check")
        result = self.run_claude_command(
            "Use netbox_health_check to check system status and connectivity"
        )
        self.print_result(result)
        return result["success"]
    
    def list_all_sites(self):
        """List alle NetBox sites"""
        print("\n🏢 Listing All NetBox Sites")
        result = self.run_claude_command(
            "Use netbox_list_all_sites to show all sites with their status"
        )
        self.print_result(result)
        return result["success"]
    
    def get_site_info(self, site_name: str):
        """Get detailed info voor specific site"""
        print(f"\n🔍 Getting Site Info for: {site_name}")
        result = self.run_claude_command(
            f"Use netbox_get_site_info to get detailed information for site '{site_name}'"
        )
        self.print_result(result)
        return result["success"]
    
    def list_racks_for_site(self, site_name: str):
        """List alle racks voor specific site"""
        print(f"\n🗄️ Listing Racks for Site: {site_name}")
        result = self.run_claude_command(
            f"Use netbox_list_all_racks with site_name='{site_name}' to show all racks"
        )
        self.print_result(result)
        return result["success"]
    
    def get_rack_inventory(self, site_name: str, rack_name: str):
        """Get rack inventory voor specific rack"""
        print(f"\n📦 Getting Rack Inventory: {rack_name} in {site_name}")
        result = self.run_claude_command(
            f"Use netbox_get_rack_inventory for site_name='{site_name}' and rack_name='{rack_name}'"
        )
        self.print_result(result)
        return result["success"]
    
    def list_devices(self, site_name: Optional[str] = None, limit: int = 20):
        """List devices, optionally filtered by site"""
        if site_name:
            print(f"\n💻 Listing Devices for Site: {site_name}")
            prompt = f"Use netbox_list_all_devices with site_name='{site_name}' and limit={limit}"
        else:
            print(f"\n💻 Listing All Devices (limit: {limit})")
            prompt = f"Use netbox_list_all_devices with limit={limit}"
            
        result = self.run_claude_command(prompt)
        self.print_result(result)
        return result["success"]
    
    def get_device_info(self, device_name: str):
        """Get detailed device information"""
        print(f"\n🔍 Getting Device Info: {device_name}")
        result = self.run_claude_command(
            f"Use netbox_get_device_info for device_name='{device_name}'"
        )
        self.print_result(result)
        return result["success"]
    
    def list_ip_prefixes(self, site_name: Optional[str] = None):
        """List IP prefixes, optionally filtered by site"""
        if site_name:
            print(f"\n🌐 Listing IP Prefixes for Site: {site_name}")
            prompt = f"Use netbox_list_all_prefixes with site_name='{site_name}'"
        else:
            print("\n🌐 Listing All IP Prefixes")
            prompt = "Use netbox_list_all_prefixes"
            
        result = self.run_claude_command(prompt)
        self.print_result(result)
        return result["success"]
    
    def find_available_ips(self, prefix: str, count: int = 5):
        """Find available IP addresses in prefix"""
        print(f"\n🔍 Finding Available IPs in: {prefix}")
        result = self.run_claude_command(
            f"Use netbox_find_available_ip for prefix='{prefix}' with count={count}"
        )
        self.print_result(result)
        return result["success"]
    
    def interactive_menu(self):
        """Main interactive menu"""
        while True:
            print("\n" + "="*60)
            print("🤖 NetBox MCP Interactive Automation")
            print("="*60)
            print("1.  System Health Check")
            print("2.  List All Sites")
            print("3.  Get Site Information")
            print("4.  List Racks for Site")
            print("5.  Get Rack Inventory")
            print("6.  List Devices")
            print("7.  Get Device Information")
            print("8.  List IP Prefixes")
            print("9.  Find Available IPs")
            print("10. Custom NetBox Command")
            print("0.  Exit")
            print("-"*60)
            
            try:
                choice = input("Selecteer een optie (0-10): ").strip()
                
                if choice == "0":
                    print("👋 Goodbye!")
                    break
                elif choice == "1":
                    self.system_health_check()
                elif choice == "2":
                    self.list_all_sites()
                elif choice == "3":
                    site_name = input("Site naam: ").strip()
                    if site_name:
                        self.get_site_info(site_name)
                    else:
                        print("❌ Site naam is verplicht")
                elif choice == "4":
                    site_name = input("Site naam: ").strip()
                    if site_name:
                        self.list_racks_for_site(site_name)
                    else:
                        print("❌ Site naam is verplicht")
                elif choice == "5":
                    site_name = input("Site naam: ").strip()
                    rack_name = input("Rack naam: ").strip()
                    if site_name and rack_name:
                        self.get_rack_inventory(site_name, rack_name)
                    else:
                        print("❌ Beide site en rack naam zijn verplicht")
                elif choice == "6":
                    site_name = input("Site naam (optioneel, Enter voor alle): ").strip()
                    limit_str = input("Limit (default 20): ").strip()
                    limit = int(limit_str) if limit_str.isdigit() else 20
                    self.list_devices(site_name if site_name else None, limit)
                elif choice == "7":
                    device_name = input("Device naam: ").strip()
                    if device_name:
                        self.get_device_info(device_name)
                    else:
                        print("❌ Device naam is verplicht")
                elif choice == "8":
                    site_name = input("Site naam (optioneel, Enter voor alle): ").strip()
                    self.list_ip_prefixes(site_name if site_name else None)
                elif choice == "9":
                    prefix = input("IP Prefix (bijv. 10.0.1.0/24): ").strip()
                    count_str = input("Aantal IPs (default 5): ").strip()
                    count = int(count_str) if count_str.isdigit() else 5
                    if prefix:
                        self.find_available_ips(prefix, count)
                    else:
                        print("❌ IP Prefix is verplicht")
                elif choice == "10":
                    custom_command = input("Custom NetBox MCP command: ").strip()
                    if custom_command:
                        result = self.run_claude_command(custom_command)
                        self.print_result(result)
                    else:
                        print("❌ Command is verplicht")
                else:
                    print("❌ Ongeldige keuze, probeer opnieuw")
                    
            except KeyboardInterrupt:
                print("\n👋 Interrupted by user, goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def run_workflow(self, workflow_name: str):
        """Run een predefined workflow"""
        workflows = {
            "site_overview": self._site_overview_workflow,
            "device_check": self._device_check_workflow,
            "network_audit": self._network_audit_workflow
        }
        
        if workflow_name in workflows:
            print(f"\n🚀 Running workflow: {workflow_name}")
            workflows[workflow_name]()
        else:
            print(f"❌ Unknown workflow: {workflow_name}")
            print(f"Available workflows: {', '.join(workflows.keys())}")
    
    def _site_overview_workflow(self):
        """Workflow: Complete site overview"""
        print("📋 Site Overview Workflow")
        
        # Step 1: Health check
        if not self.system_health_check():
            print("❌ Health check failed, stopping workflow")
            return
        
        # Step 2: List sites
        if not self.list_all_sites():
            print("❌ Could not list sites, stopping workflow")
            return
        
        # Step 3: Ask for specific site
        site_name = input("\nWelke site wil je in detail bekijken? ").strip()
        if site_name:
            self.get_site_info(site_name)
            self.list_racks_for_site(site_name)
            self.list_devices(site_name, 10)
        
        print("✅ Site overview workflow completed")
    
    def _device_check_workflow(self):
        """Workflow: Device information check"""
        print("📋 Device Check Workflow")
        
        # Step 1: List devices
        site_name = input("Site naam (optioneel): ").strip()
        self.list_devices(site_name if site_name else None, 10)
        
        # Step 2: Get specific device info
        device_name = input("\nWelke device wil je in detail bekijken? ").strip()
        if device_name:
            self.get_device_info(device_name)
        
        print("✅ Device check workflow completed")
    
    def _network_audit_workflow(self):
        """Workflow: Network configuration audit"""
        print("📋 Network Audit Workflow")
        
        # Step 1: List prefixes
        site_name = input("Site naam (optioneel): ").strip()
        self.list_ip_prefixes(site_name if site_name else None)
        
        # Step 2: Check specific prefix
        prefix = input("\nWelke prefix wil je controleren voor beschikbare IPs? ").strip()
        if prefix:
            self.find_available_ips(prefix, 10)
        
        print("✅ Network audit workflow completed")


def main():
    """Main function"""
    if len(sys.argv) > 1:
        # Command line mode
        automation = NetBoxMCPAutomation()
        
        if sys.argv[1] == "workflow" and len(sys.argv) > 2:
            automation.run_workflow(sys.argv[2])
        else:
            command = " ".join(sys.argv[1:])
            result = automation.run_claude_command(command)
            automation.print_result(result)
    else:
        # Interactive mode
        automation = NetBoxMCPAutomation()
        print("🤖 NetBox MCP Interactive Automation Script")
        print("Dit script gebruikt Claude Code om NetBox MCP taken uit te voeren")
        print("\nZorg ervoor dat:")
        print("- Claude Code is geïnstalleerd en in je PATH")
        print("- NetBox MCP server is gestart")
        print("- MCP configuratie is correct ingesteld")
        
        # Check if Claude is available
        result = automation.run_claude_command("--version")
        if not result["success"]:
            print(f"\n❌ Could not run Claude Code: {result['error']}")
            print("Please make sure Claude Code is installed and configured correctly")
            sys.exit(1)
        
        automation.interactive_menu()


if __name__ == "__main__":
    main()