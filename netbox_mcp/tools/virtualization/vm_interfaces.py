#!/usr/bin/env python3
"""
Virtual Machine Interface Management Tools

High-level tools for managing NetBox virtual machine interfaces,
enabling comprehensive VM network connectivity and configuration management.
"""

from typing import Dict, Optional, Any, List
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)


@mcp_tool(category="virtualization")
def netbox_create_vm_interface(
    client: NetBoxClient,
    virtual_machine_name: str,
    interface_name: str,
    interface_type: str = "virtual",
    enabled: bool = True,
    mtu: Optional[int] = None,
    mac_address: Optional[str] = None,
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a new interface for a virtual machine in NetBox.
    
    VM interfaces enable network connectivity configuration and IP address assignment
    for virtual machines within the virtualization infrastructure.
    
    Args:
        client: NetBoxClient instance (injected)
        virtual_machine_name: Name of the virtual machine
        interface_name: Interface name (e.g., "eth0", "nic1", "mgmt")
        interface_type: Interface type (virtual, bridge, lag, etc.)
        enabled: Whether the interface is enabled (default: True)
        mtu: Maximum Transmission Unit size
        mac_address: MAC address for the interface
        description: Optional description of the interface
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Dict containing the created VM interface data
        
    Raises:
        ValidationError: If required parameters are missing or invalid
        NotFoundError: If virtual machine not found
        ConflictError: If interface already exists
    """
    
    # STEP 1: DRY RUN CHECK
    if not confirm:
        return {
            "success": True,
            "dry_run": True,
            "message": "DRY RUN: VM interface would be created. Set confirm=True to execute.",
            "would_create": {
                "virtual_machine": virtual_machine_name,
                "interface_name": interface_name,
                "interface_type": interface_type,
                "enabled": enabled,
                "mtu": mtu,
                "mac_address": mac_address,
                "description": f"[NetBox-MCP] {description}" if description else ""
            }
        }
    
    # STEP 2: PARAMETER VALIDATION
    if not virtual_machine_name or not virtual_machine_name.strip():
        raise ValueError("virtual_machine_name cannot be empty")
    
    if not interface_name or not interface_name.strip():
        raise ValueError("interface_name cannot be empty")
    
    # STEP 3: LOOKUP VIRTUAL MACHINE
    try:
        virtual_machines = client.virtualization.virtual_machines.filter(name=virtual_machine_name)
        if not virtual_machines:
            raise ValueError(f"Virtual machine '{virtual_machine_name}' not found")
        
        virtual_machine = virtual_machines[0]
        vm_id = virtual_machine.get('id') if isinstance(virtual_machine, dict) else virtual_machine.id
        vm_display = virtual_machine.get('display', virtual_machine_name) if isinstance(virtual_machine, dict) else getattr(virtual_machine, 'display', virtual_machine_name)
        
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Could not find virtual machine '{virtual_machine_name}': {e}")
    
    # STEP 4: CONFLICT DETECTION
    try:
        existing_interfaces = client.virtualization.interfaces.filter(
            virtual_machine_id=vm_id,
            name=interface_name,
            no_cache=True
        )
        
        if existing_interfaces:
            existing_interface = existing_interfaces[0]
            existing_id = existing_interface.get('id') if isinstance(existing_interface, dict) else existing_interface.id
            raise ValueError(f"Interface '{interface_name}' already exists on VM '{virtual_machine_name}' with ID {existing_id}")
            
    except ValueError:
        raise
    except Exception as e:
        logger.warning(f"Could not check for existing VM interfaces: {e}")
    
    # STEP 5: CREATE VM INTERFACE
    create_payload = {
        "virtual_machine": vm_id,
        "name": interface_name,
        "enabled": enabled
    }
    
    # Handle interface type - NetBox VM interfaces use specific type format
    # For VM interfaces, common types are: virtual, bridge, lag, 1000base-t, etc.
    # NetBox expects the type as a simple string value
    if interface_type:
        create_payload["type"] = interface_type
        logger.debug(f"Setting interface type: {interface_type}")
    
    if mtu:
        create_payload["mtu"] = mtu
    
    if mac_address:
        # Ensure MAC address is in proper format for NetBox
        # NetBox expects MAC addresses in uppercase with colons
        mac_address_clean = mac_address.strip().upper().replace('-', ':').replace('.', ':')
        # Ensure proper MAC format (XX:XX:XX:XX:XX:XX)
        if len(mac_address_clean.replace(':', '')) == 12:
            if ':' not in mac_address_clean:
                # Convert XXXXXXXXXXXX to XX:XX:XX:XX:XX:XX
                mac_address_clean = ':'.join([mac_address_clean[i:i+2] for i in range(0, 12, 2)])
            create_payload["mac_address"] = mac_address_clean
            logger.debug(f"Setting MAC address: {mac_address_clean}")
        else:
            logger.warning(f"Invalid MAC address format: {mac_address}, skipping")
    
    if description:
        create_payload["description"] = f"[NetBox-MCP] {description}"
    
    try:
        # Log the payload for debugging
        logger.debug(f"Creating VM interface with payload: {create_payload}")
        
        # Ensure type is properly set for NetBox API
        if "type" in create_payload:
            logger.debug(f"Interface type being sent to API: {create_payload['type']}")
        
        # Ensure MAC address is properly set for NetBox API
        if "mac_address" in create_payload:
            logger.debug(f"MAC address being sent to API: {create_payload['mac_address']}")
        
        new_interface = client.virtualization.interfaces.create(confirm=confirm, **create_payload)
        
        # Apply defensive dict/object handling
        interface_id = new_interface.get('id') if isinstance(new_interface, dict) else new_interface.id
        interface_name_created = new_interface.get('name') if isinstance(new_interface, dict) else new_interface.name
        interface_type_created = new_interface.get('type') if isinstance(new_interface, dict) else getattr(new_interface, 'type', None)
        interface_mac_created = new_interface.get('mac_address') if isinstance(new_interface, dict) else getattr(new_interface, 'mac_address', None)
        
        # Log what was actually created for debugging
        logger.debug(f"Created interface - ID: {interface_id}, Type: {interface_type_created}, MAC: {interface_mac_created}")
        
        # Check if type was properly stored
        if interface_type and interface_type_created != interface_type:
            logger.warning(f"Interface type mismatch - Expected: {interface_type}, Got: {interface_type_created}")
        
        # Check if MAC address was properly stored
        if mac_address and not interface_mac_created:
            logger.warning(f"MAC address not stored - Expected: {mac_address}, Got: {interface_mac_created}")
        elif mac_address and interface_mac_created:
            logger.debug(f"MAC address successfully stored: {interface_mac_created}")
        
    except Exception as e:
        raise ValueError(f"NetBox API error during VM interface creation: {e}")
    
    # STEP 6: RETURN SUCCESS
    return {
        "success": True,
        "message": f"VM interface '{interface_name}' successfully created for '{virtual_machine_name}'.",
        "data": {
            "interface_id": interface_id,
            "interface_name": interface_name_created,
            "interface_type": interface_type_created,
            "virtual_machine_id": vm_id,
            "virtual_machine_name": virtual_machine_name,
            "enabled": new_interface.get('enabled') if isinstance(new_interface, dict) else getattr(new_interface, 'enabled', None),
            "mac_address": interface_mac_created,
            "description": new_interface.get('description') if isinstance(new_interface, dict) else getattr(new_interface, 'description', None)
        }
    }


@mcp_tool(category="virtualization")
def netbox_get_vm_interface_info(
    client: NetBoxClient,
    virtual_machine_name: Optional[str] = None,
    interface_name: Optional[str] = None,
    interface_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific VM interface.
    
    Args:
        client: NetBoxClient instance (injected)
        virtual_machine_name: Virtual machine name (used with interface_name)
        interface_name: Interface name to retrieve
        interface_id: Interface ID to retrieve
        
    Returns:
        Dict containing detailed VM interface information
        
    Raises:
        ValidationError: If no valid identifier provided
        NotFoundError: If VM interface not found
    """
    
    if interface_id:
        try:
            vm_interface = client.virtualization.interfaces.get(interface_id)
        except Exception as e:
            raise ValueError(f"VM interface with ID {interface_id} not found: {e}")
    elif virtual_machine_name and interface_name:
        try:
            # First find the VM
            virtual_machines = client.virtualization.virtual_machines.filter(name=virtual_machine_name)
            if not virtual_machines:
                raise ValueError(f"Virtual machine '{virtual_machine_name}' not found")
            
            vm = virtual_machines[0]
            vm_id = vm.get('id') if isinstance(vm, dict) else vm.id
            
            # Then find the interface
            interfaces = client.virtualization.interfaces.filter(
                virtual_machine_id=vm_id,
                name=interface_name
            )
            if not interfaces:
                raise ValueError(f"Interface '{interface_name}' not found on VM '{virtual_machine_name}'")
            
            vm_interface = interfaces[0]
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to find VM interface: {e}")
    else:
        raise ValueError("Either 'interface_id' or both 'virtual_machine_name' and 'interface_name' must be provided")
    
    # Apply defensive dict/object handling
    interface_id = vm_interface.get('id') if isinstance(vm_interface, dict) else vm_interface.id
    interface_name = vm_interface.get('name') if isinstance(vm_interface, dict) else vm_interface.name
    interface_type = vm_interface.get('type') if isinstance(vm_interface, dict) else getattr(vm_interface, 'type', None)
    interface_enabled = vm_interface.get('enabled') if isinstance(vm_interface, dict) else getattr(vm_interface, 'enabled', None)
    interface_mtu = vm_interface.get('mtu') if isinstance(vm_interface, dict) else getattr(vm_interface, 'mtu', None)
    interface_mac = vm_interface.get('mac_address') if isinstance(vm_interface, dict) else getattr(vm_interface, 'mac_address', None)
    interface_description = vm_interface.get('description') if isinstance(vm_interface, dict) else getattr(vm_interface, 'description', None)
    
    # Get virtual machine information - with proper resolution
    vm_obj = vm_interface.get('virtual_machine') if isinstance(vm_interface, dict) else getattr(vm_interface, 'virtual_machine', None)
    
    # Try to get VM ID first
    if isinstance(vm_obj, dict):
        vm_id = vm_obj.get('id')
        vm_name = vm_obj.get('name', 'N/A')
    else:
        vm_id = getattr(vm_obj, 'id', None) if vm_obj else None
        vm_name = getattr(vm_obj, 'name', None) if vm_obj else None
    
    # If we don't have proper VM name, fetch it directly from the API
    if not vm_name or vm_name == 'N/A' or str(vm_name).isdigit():
        try:
            if vm_id and vm_id != 'N/A':
                vm_full = client.virtualization.virtual_machines.get(vm_id)
                vm_name = vm_full.get('name') if isinstance(vm_full, dict) else vm_full.name
                logger.debug(f"Fetched VM name from API: {vm_name} for ID {vm_id}")
            else:
                vm_name = 'N/A'
                vm_id = 'N/A'
        except Exception as e:
            logger.warning(f"Failed to fetch VM name for ID {vm_id}: {e}")
            vm_name = 'N/A'
            vm_id = vm_id or 'N/A'
    
    # Get IP addresses assigned to this interface
    try:
        ip_addresses = list(client.ipam.ip_addresses.filter(assigned_object_id=interface_id))
        ip_count = len(ip_addresses)
        ip_list = []
        for ip in ip_addresses[:5]:  # Show first 5 IPs
            ip_addr = ip.get('address') if isinstance(ip, dict) else getattr(ip, 'address', 'N/A')
            ip_list.append(ip_addr)
    except Exception:
        ip_count = 0
        ip_list = []
    
    return {
        "success": True,
        "message": f"Retrieved VM interface '{interface_name}'.",
        "data": {
            "interface_id": interface_id,
            "name": interface_name,
            "type": interface_type,
            "enabled": interface_enabled,
            "mtu": interface_mtu,
            "mac_address": interface_mac,
            "description": interface_description,
            "virtual_machine": {
                "id": vm_id,
                "name": vm_name
            },
            "ip_addresses": {
                "count": ip_count,
                "addresses": ip_list
            },
            "url": vm_interface.get('url') if isinstance(vm_interface, dict) else getattr(vm_interface, 'url', None)
        }
    }


@mcp_tool(category="virtualization")
def netbox_list_all_vm_interfaces(
    client: NetBoxClient,
    virtual_machine_name: Optional[str] = None,
    interface_type: Optional[str] = None,
    enabled: Optional[bool] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Get comprehensive list of all VM interfaces with filtering capabilities.
    
    This tool provides bulk VM interface discovery across the virtualization infrastructure,
    enabling efficient network connectivity analysis and interface management.
    
    Args:
        client: NetBoxClient instance (injected)
        virtual_machine_name: Filter by virtual machine name
        interface_type: Filter by interface type (virtual, bridge, lag, etc.)
        enabled: Filter by enabled status (True/False)
        limit: Maximum number of interfaces to return (default: 100)
        
    Returns:
        Dict containing summary list of VM interfaces with statistics
    """
    
    # Build filter parameters
    filter_params = {}
    
    if virtual_machine_name:
        # First find the VM ID
        try:
            vms = client.virtualization.virtual_machines.filter(name=virtual_machine_name)
            if not vms:
                raise ValueError(f"Virtual machine '{virtual_machine_name}' not found")
            vm = vms[0]
            vm_id = vm.get('id') if isinstance(vm, dict) else vm.id
            filter_params["virtual_machine_id"] = vm_id
        except Exception as e:
            raise ValueError(f"Failed to find virtual machine: {e}")
    
    if interface_type:
        filter_params["type"] = interface_type
    
    if enabled is not None:
        filter_params["enabled"] = enabled
    
    try:
        # Get VM interfaces with applied filters
        vm_interfaces = list(client.virtualization.interfaces.filter(**filter_params)[:limit])
        
        # Process interfaces with defensive dict/object handling
        interfaces_summary = []
        total_enabled = 0
        total_disabled = 0
        type_counts = {}
        
        for interface in vm_interfaces:
            interface_id = interface.get('id') if isinstance(interface, dict) else interface.id
            interface_name = interface.get('name') if isinstance(interface, dict) else interface.name
            interface_type_actual = interface.get('type') if isinstance(interface, dict) else getattr(interface, 'type', 'N/A')
            interface_enabled = interface.get('enabled') if isinstance(interface, dict) else getattr(interface, 'enabled', False)
            interface_mac = interface.get('mac_address') if isinstance(interface, dict) else getattr(interface, 'mac_address', None)
            
            # Count by status
            if interface_enabled:
                total_enabled += 1
            else:
                total_disabled += 1
            
            # Count by type
            type_counts[interface_type_actual] = type_counts.get(interface_type_actual, 0) + 1
            
            # Get VM information - with proper resolution
            vm_obj = interface.get('virtual_machine') if isinstance(interface, dict) else getattr(interface, 'virtual_machine', None)
            if isinstance(vm_obj, dict):
                vm_id = vm_obj.get('id')
                vm_name = vm_obj.get('name', 'N/A')
            else:
                vm_id = getattr(vm_obj, 'id', None) if vm_obj else None
                vm_name = getattr(vm_obj, 'name', None) if vm_obj else None
            
            # If we don't have proper VM name, fetch it directly
            if not vm_name or vm_name == 'N/A' or str(vm_name).isdigit():
                try:
                    if vm_id and vm_id != 'N/A':
                        vm_full = client.virtualization.virtual_machines.get(vm_id)
                        vm_name = vm_full.get('name') if isinstance(vm_full, dict) else vm_full.name
                        logger.debug(f"Fetched VM name from API in list: {vm_name} for ID {vm_id}")
                    else:
                        vm_name = 'N/A'
                except Exception as e:
                    logger.warning(f"Failed to fetch VM name in list for ID {vm_id}: {e}")
                    vm_name = 'N/A'
            
            # Count IP addresses for this interface
            try:
                ip_count = len(list(client.ipam.ip_addresses.filter(assigned_object_id=interface_id)))
            except Exception:
                ip_count = 0
            
            interfaces_summary.append({
                "id": interface_id,
                "name": interface_name,
                "type": interface_type_actual,
                "enabled": interface_enabled,
                "mac_address": interface_mac,
                "virtual_machine_name": vm_name,
                "ip_address_count": ip_count
            })
            
    except Exception as e:
        raise ValueError(f"Failed to retrieve VM interfaces: {e}")
    
    return {
        "success": True,
        "message": f"Found {len(interfaces_summary)} VM interfaces.",
        "total_interfaces": len(interfaces_summary),
        "statistics": {
            "enabled_interfaces": total_enabled,
            "disabled_interfaces": total_disabled,
            "interface_types": type_counts
        },
        "applied_filters": {
            "virtual_machine_name": virtual_machine_name,
            "interface_type": interface_type,
            "enabled": enabled,
            "limit": limit
        },
        "data": interfaces_summary
    }


@mcp_tool(category="virtualization")
def netbox_update_vm_interface(
    client: NetBoxClient,
    interface_id: int,
    interface_name: Optional[str] = None,
    interface_type: Optional[str] = None,
    enabled: Optional[bool] = None,
    mtu: Optional[int] = None,
    mac_address: Optional[str] = None,
    description: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Update an existing VM interface in NetBox.
    
    Args:
        client: NetBoxClient instance (injected)
        interface_id: ID of the VM interface to update
        interface_name: New name for the interface
        interface_type: New type for the interface
        enabled: New enabled status
        mtu: New MTU size
        mac_address: New MAC address
        description: New description for the interface
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Dict containing the updated VM interface data
    """
    
    # STEP 1: DRY RUN CHECK
    if not confirm:
        update_fields = {}
        if interface_name: update_fields["name"] = interface_name
        if interface_type: update_fields["type"] = interface_type
        if enabled is not None: update_fields["enabled"] = enabled
        if mtu: update_fields["mtu"] = mtu
        if mac_address: update_fields["mac_address"] = mac_address
        if description: update_fields["description"] = f"[NetBox-MCP] {description}"
        
        return {
            "success": True,
            "dry_run": True,
            "message": "DRY RUN: VM interface would be updated. Set confirm=True to execute.",
            "would_update": {
                "interface_id": interface_id,
                "fields": update_fields
            }
        }
    
    # STEP 2: PARAMETER VALIDATION
    if not interface_id or interface_id <= 0:
        raise ValueError("interface_id must be a positive integer")
    
    if not any([interface_name, interface_type, enabled is not None, mtu, mac_address, description is not None]):
        raise ValueError("At least one field must be provided for update")
    
    # STEP 3: BUILD UPDATE PAYLOAD
    update_payload = {}
    
    if interface_name:
        if not interface_name.strip():
            raise ValueError("interface_name cannot be empty")
        update_payload["name"] = interface_name
    
    if interface_type:
        update_payload["type"] = interface_type
    
    if enabled is not None:
        update_payload["enabled"] = enabled
    
    if mtu:
        update_payload["mtu"] = mtu
    
    if mac_address:
        update_payload["mac_address"] = mac_address
    
    if description is not None:
        update_payload["description"] = f"[NetBox-MCP] {description}" if description else ""
    
    # STEP 4: UPDATE VM INTERFACE
    try:
        updated_interface = client.virtualization.interfaces.update(interface_id, confirm=confirm, **update_payload)
        
        # Apply defensive dict/object handling
        interface_id_updated = updated_interface.get('id') if isinstance(updated_interface, dict) else updated_interface.id
        interface_name_updated = updated_interface.get('name') if isinstance(updated_interface, dict) else updated_interface.name
        interface_type_updated = updated_interface.get('type') if isinstance(updated_interface, dict) else getattr(updated_interface, 'type', None)
        
    except Exception as e:
        raise ValueError(f"NetBox API error during VM interface update: {e}")
    
    # STEP 5: RETURN SUCCESS
    return {
        "success": True,
        "message": f"VM interface ID {interface_id} successfully updated.",
        "data": {
            "interface_id": interface_id_updated,
            "name": interface_name_updated,
            "type": interface_type_updated,
            "enabled": updated_interface.get('enabled') if isinstance(updated_interface, dict) else getattr(updated_interface, 'enabled', None),
            "mtu": updated_interface.get('mtu') if isinstance(updated_interface, dict) else getattr(updated_interface, 'mtu', None),
            "mac_address": updated_interface.get('mac_address') if isinstance(updated_interface, dict) else getattr(updated_interface, 'mac_address', None)
        }
    }


@mcp_tool(category="virtualization")
def netbox_delete_vm_interface(
    client: NetBoxClient,
    interface_id: int,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Delete a VM interface from NetBox.
    
    Args:
        client: NetBoxClient instance (injected)
        interface_id: ID of the VM interface to delete
        confirm: Must be True to execute (safety mechanism)
        
    Returns:
        Dict containing deletion confirmation
        
    Raises:
        ValidationError: If interface has assigned IP addresses
    """
    
    # STEP 1: DRY RUN CHECK
    if not confirm:
        return {
            "success": True,
            "dry_run": True,
            "message": "DRY RUN: VM interface would be deleted. Set confirm=True to execute.",
            "would_delete": {
                "interface_id": interface_id
            }
        }
    
    # STEP 2: PARAMETER VALIDATION
    if not interface_id or interface_id <= 0:
        raise ValueError("interface_id must be a positive integer")
    
    # STEP 3: CHECK FOR DEPENDENCIES
    try:
        # Check if interface has assigned IP addresses
        assigned_ips = list(client.ipam.ip_addresses.filter(assigned_object_id=interface_id))
        if assigned_ips:
            ip_addresses = []
            for ip in assigned_ips[:5]:  # Show first 5
                ip_addr = ip.get('address') if isinstance(ip, dict) else getattr(ip, 'address', 'N/A')
                ip_addresses.append(ip_addr)
            
            raise ValueError(
                f"Cannot delete VM interface - {len(assigned_ips)} assigned IP addresses found: "
                f"{', '.join(ip_addresses)}" + 
                ("..." if len(assigned_ips) > 5 else "")
            )
        
        # Get interface info before deletion
        vm_interface = client.virtualization.interfaces.get(interface_id)
        interface_name = vm_interface.get('name') if isinstance(vm_interface, dict) else vm_interface.name
        
        # Get VM name - with proper resolution
        vm_obj = vm_interface.get('virtual_machine') if isinstance(vm_interface, dict) else getattr(vm_interface, 'virtual_machine', None)
        if isinstance(vm_obj, dict):
            vm_id = vm_obj.get('id')
            vm_name = vm_obj.get('name', 'N/A')
        else:
            vm_id = getattr(vm_obj, 'id', None) if vm_obj else None
            vm_name = getattr(vm_obj, 'name', None) if vm_obj else None
        
        # If we don't have proper VM name, fetch it directly
        if not vm_name or vm_name == 'N/A' or str(vm_name).isdigit():
            try:
                if vm_id and vm_id != 'N/A':
                    vm_full = client.virtualization.virtual_machines.get(vm_id)
                    vm_name = vm_full.get('name') if isinstance(vm_full, dict) else vm_full.name
                    logger.debug(f"Fetched VM name from API in delete: {vm_name} for ID {vm_id}")
                else:
                    vm_name = 'N/A'
            except Exception as e:
                logger.warning(f"Failed to fetch VM name in delete for ID {vm_id}: {e}")
                vm_name = 'N/A'
        
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to validate VM interface for deletion: {e}")
    
    # STEP 4: DELETE VM INTERFACE
    try:
        client.virtualization.interfaces.delete(interface_id, confirm=confirm)
        
    except Exception as e:
        raise ValueError(f"NetBox API error during VM interface deletion: {e}")
    
    # STEP 5: RETURN SUCCESS
    return {
        "success": True,
        "message": f"VM interface '{interface_name}' on '{vm_name}' (ID: {interface_id}) successfully deleted.",
        "data": {
            "deleted_interface_id": interface_id,
            "deleted_interface_name": interface_name,
            "virtual_machine_name": vm_name
        }
    }