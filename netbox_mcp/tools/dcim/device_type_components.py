"""
Device Type Component Templates Management Tools

This module provides enterprise-grade tools for managing NetBox Device Type component templates.
These tools enable complete standardization of device infrastructure by defining the physical
and logical components that should be present on all devices of a specific type.

Component templates supported:
- Interface Templates: Network interfaces (ethernet, fiber, etc.)
- Console Port Templates: Serial console ports
- Power Port Templates: Power inlet ports (PSUs)
- Console Server Port Templates: Out-of-band serial management ports
- Power Outlet Templates: Power outlet ports (PDUs)
- Front Port Templates: Physical front-facing ports (patch panels)
- Rear Port Templates: Physical rear-facing ports
- Device Bay Templates: Child device bays (blade chassis)
- Module Bay Templates: Modular component bays (line cards)
"""

from netbox_mcp.registry import mcp_tool
from netbox_mcp.client import NetBoxClient
from netbox_mcp.exceptions import (
    NetBoxValidationError as ValidationError, 
    NetBoxNotFoundError as NotFoundError, 
    NetBoxConflictError as ConflictError
)
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


@mcp_tool(category="dcim")
def netbox_add_interface_template_to_device_type(
    device_type_model: str,
    name: str,
    type: str,
    description: Optional[str] = None,
    mgmt_only: bool = False,
    client: NetBoxClient = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Add a new Interface Template to an existing Device Type.

    This tool defines a standardized network port for all devices of a specific model.
    Interface templates are essential for network device standardization and automated
    provisioning workflows.

    Args:
        device_type_model (str): The model name of the Device Type (e.g., "Cisco C9300-24T").
        name (str): The name of the interface (e.g., "GigabitEthernet0/1", "eth0").
        type (str): The physical type of the interface (e.g., "1000base-t", "10gbase-x-sfpp").
        description (str, optional): A description for the interface template.
        mgmt_only (bool): Whether this interface is management-only. Defaults to False.
        client (NetBoxClient): The active NetBox client.
        confirm (bool): Must be True to execute the operation.

    Returns:
        dict: A dictionary containing the operation result and created template data.
    
    Raises:
        ValidationError: If required parameters are missing or invalid.
        ConflictError: If an interface template with the same name already exists.
        NotFoundError: If the specified Device Type cannot be found.
    """
    if not confirm:
        return {
            "status": "dry_run",
            "message": "DRY RUN: Interface Template would be created. Set confirm=True to execute.",
            "would_create": {
                "device_type_model": device_type_model,
                "interface_name": name,
                "interface_type": type,
                "description": description,
                "mgmt_only": mgmt_only
            }
        }

    # STEP 1: VALIDATE - Find the Device Type by model name
    logger.info(f"Looking up Device Type with model: {device_type_model}")
    
    try:
        device_types = client.dcim.device_types.filter(model=device_type_model)
        if not device_types:
            raise NotFoundError(f"Device Type with model '{device_type_model}' not found.")
        
        device_type = device_types[0]
        logger.info(f"Found Device Type: {device_type.display} (ID: {device_type.id})")
        
    except Exception as e:
        logger.error(f"Error looking up Device Type: {e}")
        raise NotFoundError(f"Could not find Device Type '{device_type_model}': {e}")

    # STEP 2: DEFENSIVE READ - Check for conflicts (does this template already exist?)
    logger.info(f"Checking for existing Interface Template '{name}' on Device Type '{device_type_model}'")
    
    try:
        existing_templates = client.dcim.interface_templates.filter(
            device_type_id=device_type.id,
            name=name,
            no_cache=True  # Force live check for accurate conflict detection
        )
        
        if existing_templates:
            existing_template = existing_templates[0]
            logger.warning(f"Interface Template conflict detected: '{name}' already exists for Device Type '{device_type_model}' (ID: {existing_template.id})")
            raise ConflictError(
                resource_type="Interface Template",
                identifier=f"{name} for Device Type {device_type_model}",
                existing_id=existing_template.id
            )
            
    except ConflictError:
        raise
    except Exception as e:
        logger.warning(f"Could not check for existing templates: {e}")

    # STEP 3: VALIDATE PARAMETERS - Check interface type is valid
    if not type:
        raise ValidationError("Interface type is required and cannot be empty.")
    
    if not name:
        raise ValidationError("Interface name is required and cannot be empty.")

    # STEP 4: WRITE - Create the Interface Template
    template_payload = {
        "device_type": device_type.id,
        "name": name,
        "type": type,
        "description": description or "",
        "mgmt_only": mgmt_only
    }
    
    try:
        logger.info(f"Creating Interface Template '{name}' for Device Type '{device_type_model}'...")
        new_template = client.dcim.interface_templates.create(**template_payload)
        logger.info(f"Successfully created Interface Template with ID: {new_template.id}")
        
    except Exception as e:
        logger.error(f"Failed to create Interface Template in NetBox: {e}")
        raise ValidationError(f"NetBox API error during Interface Template creation: {e}")

    # STEP 5: CACHE INVALIDATION - Invalidate cache for the Device Type
    try:
        client.cache.invalidate_for_objects([device_type])
        logger.debug("Cache invalidated for Device Type after Interface Template creation")
    except Exception as e:
        logger.warning(f"Cache invalidation failed (non-critical): {e}")

    return {
        "status": "success",
        "message": f"Interface Template '{new_template.name}' successfully added to Device Type '{device_type_model}'.",
        "data": {
            "template_id": new_template.id,
            "template_name": new_template.name,
            "template_type": new_template.type,
            "device_type_model": device_type_model,
            "device_type_id": device_type.id,
            "description": new_template.description,
            "mgmt_only": new_template.mgmt_only,
            "netbox_url": f"{client.base_url}/dcim/device-types/{device_type.id}/interface-templates/"
        }
    }


@mcp_tool(category="dcim")
def netbox_add_console_port_template_to_device_type(
    device_type_model: str,
    name: str,
    type: str = "rj-45",
    description: Optional[str] = None,
    client: NetBoxClient = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Add a new Console Port Template to an existing Device Type.

    This tool defines a standardized serial console port for all devices of a specific model.
    Console port templates are essential for out-of-band management and device access.

    Args:
        device_type_model (str): The model name of the Device Type.
        name (str): The name of the console port (e.g., "Console", "CON1").
        type (str): The physical type of the console port. Defaults to "rj-45".
        description (str, optional): A description for the console port template.
        client (NetBoxClient): The active NetBox client.
        confirm (bool): Must be True to execute the operation.

    Returns:
        dict: A dictionary containing the operation result and created template data.
    """
    if not confirm:
        return {
            "status": "dry_run", 
            "message": "DRY RUN: Console Port Template would be created. Set confirm=True to execute.",
            "would_create": {
                "device_type_model": device_type_model,
                "console_port_name": name,
                "console_port_type": type,
                "description": description
            }
        }

    # Find Device Type
    try:
        device_types = client.dcim.device_types.filter(model=device_type_model)
        if not device_types:
            raise NotFoundError(f"Device Type with model '{device_type_model}' not found.")
        device_type = device_types[0]
    except Exception as e:
        raise NotFoundError(f"Could not find Device Type '{device_type_model}': {e}")

    # Check for conflicts
    try:
        existing_templates = client.dcim.console_port_templates.filter(
            device_type_id=device_type.id,
            name=name,
            no_cache=True
        )
        if existing_templates:
            existing_template = existing_templates[0]
            logger.warning(f"Console Port Template conflict detected: '{name}' already exists for Device Type '{device_type_model}' (ID: {existing_template.id})")
            raise ConflictError(
                resource_type="Console Port Template",
                identifier=f"{name} for Device Type {device_type_model}",
                existing_id=existing_template.id
            )
    except ConflictError:
        raise
    except Exception as e:
        logger.warning(f"Could not check for existing console port templates: {e}")

    # Create the template
    template_payload = {
        "device_type": device_type.id,
        "name": name,
        "type": type,
        "description": description or ""
    }
    
    try:
        new_template = client.dcim.console_port_templates.create(**template_payload)
        client.cache.invalidate_for_objects([device_type])
    except Exception as e:
        raise ValidationError(f"NetBox API error during Console Port Template creation: {e}")

    return {
        "status": "success",
        "message": f"Console Port Template '{new_template.name}' successfully added to Device Type '{device_type_model}'.",
        "data": {
            "template_id": new_template.id,
            "template_name": new_template.name,
            "template_type": new_template.type,
            "device_type_model": device_type_model,
            "device_type_id": device_type.id,
            "description": new_template.description,
            "netbox_url": f"{client.base_url}/dcim/device-types/{device_type.id}/console-port-templates/"
        }
    }


@mcp_tool(category="dcim")
def netbox_add_power_port_template_to_device_type(
    device_type_model: str,
    name: str,
    type: str = "iec-60320-c14",
    maximum_draw: Optional[int] = None,
    allocated_draw: Optional[int] = None,
    description: Optional[str] = None,
    client: NetBoxClient = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Add a new Power Port Template to an existing Device Type.

    This tool defines a standardized power inlet port for all devices of a specific model.
    Power port templates are essential for power infrastructure planning and management.

    Args:
        device_type_model (str): The model name of the Device Type.
        name (str): The name of the power port (e.g., "PSU1", "Power").
        type (str): The physical type of the power port. Defaults to "iec-60320-c14".
        maximum_draw (int, optional): Maximum power draw in watts.
        allocated_draw (int, optional): Allocated power draw in watts.
        description (str, optional): A description for the power port template.
        client (NetBoxClient): The active NetBox client.
        confirm (bool): Must be True to execute the operation.

    Returns:
        dict: A dictionary containing the operation result and created template data.
    """
    if not confirm:
        return {
            "status": "dry_run",
            "message": "DRY RUN: Power Port Template would be created. Set confirm=True to execute.",
            "would_create": {
                "device_type_model": device_type_model,
                "power_port_name": name,
                "power_port_type": type,
                "maximum_draw": maximum_draw,
                "allocated_draw": allocated_draw,
                "description": description
            }
        }

    # Find Device Type
    try:
        device_types = client.dcim.device_types.filter(model=device_type_model)
        if not device_types:
            raise NotFoundError(f"Device Type with model '{device_type_model}' not found.")
        device_type = device_types[0]
    except Exception as e:
        raise NotFoundError(f"Could not find Device Type '{device_type_model}': {e}")

    # Check for conflicts
    try:
        existing_templates = client.dcim.power_port_templates.filter(
            device_type_id=device_type.id,
            name=name,
            no_cache=True
        )
        if existing_templates:
            existing_template = existing_templates[0]
            logger.warning(f"Power Port Template conflict detected: '{name}' already exists for Device Type '{device_type_model}' (ID: {existing_template.id})")
            raise ConflictError(
                resource_type="Power Port Template",
                identifier=f"{name} for Device Type {device_type_model}",
                existing_id=existing_template.id
            )
    except ConflictError:
        raise
    except Exception as e:
        logger.warning(f"Could not check for existing power port templates: {e}")

    # Create the template
    template_payload = {
        "device_type": device_type.id,
        "name": name,
        "type": type,
        "description": description or ""
    }
    
    # Add optional power parameters if provided
    if maximum_draw is not None:
        template_payload["maximum_draw"] = maximum_draw
    if allocated_draw is not None:
        template_payload["allocated_draw"] = allocated_draw
    
    try:
        new_template = client.dcim.power_port_templates.create(**template_payload)
        client.cache.invalidate_for_objects([device_type])
    except Exception as e:
        raise ValidationError(f"NetBox API error during Power Port Template creation: {e}")

    return {
        "status": "success",
        "message": f"Power Port Template '{new_template.name}' successfully added to Device Type '{device_type_model}'.",
        "data": {
            "template_id": new_template.id,
            "template_name": new_template.name,
            "template_type": new_template.type,
            "device_type_model": device_type_model,
            "device_type_id": device_type.id,
            "description": new_template.description,
            "maximum_draw": getattr(new_template, 'maximum_draw', None),
            "allocated_draw": getattr(new_template, 'allocated_draw', None),
            "netbox_url": f"{client.base_url}/dcim/device-types/{device_type.id}/power-port-templates/"
        }
    }


@mcp_tool(category="dcim")
def netbox_add_console_server_port_template_to_device_type(
    device_type_model: str,
    name: str,
    type: str = "rj-45",
    description: Optional[str] = None,
    client: NetBoxClient = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Add a new Console Server Port Template to an existing Device Type.

    This tool defines a standardized console server port for all devices of a specific model.
    Console server port templates are used for out-of-band serial management connections.

    Args:
        device_type_model (str): The model name of the Device Type.
        name (str): The name of the console server port (e.g., "ttyS1", "Serial1").
        type (str): The physical type of the console server port. Defaults to "rj-45".
        description (str, optional): A description for the console server port template.
        client (NetBoxClient): The active NetBox client.
        confirm (bool): Must be True to execute the operation.

    Returns:
        dict: A dictionary containing the operation result and created template data.
    """
    if not confirm:
        return {
            "status": "dry_run",
            "message": "DRY RUN: Console Server Port Template would be created. Set confirm=True to execute.",
            "would_create": {
                "device_type_model": device_type_model,
                "console_server_port_name": name,
                "console_server_port_type": type,
                "description": description
            }
        }

    # Find Device Type
    try:
        device_types = client.dcim.device_types.filter(model=device_type_model)
        if not device_types:
            raise NotFoundError(f"Device Type with model '{device_type_model}' not found.")
        device_type = device_types[0]
    except Exception as e:
        raise NotFoundError(f"Could not find Device Type '{device_type_model}': {e}")

    # Check for conflicts
    try:
        existing_templates = client.dcim.console_server_port_templates.filter(
            device_type_id=device_type.id,
            name=name,
            no_cache=True
        )
        if existing_templates:
            existing_template = existing_templates[0]
            logger.warning(f"Console Server Port Template conflict detected: '{name}' already exists for Device Type '{device_type_model}' (ID: {existing_template.id})")
            raise ConflictError(
                resource_type="Console Server Port Template",
                identifier=f"{name} for Device Type {device_type_model}",
                existing_id=existing_template.id
            )
    except ConflictError:
        raise
    except Exception as e:
        logger.warning(f"Could not check for existing console server port templates: {e}")

    # Create the template
    template_payload = {
        "device_type": device_type.id,
        "name": name,
        "type": type,
        "description": description or ""
    }
    
    try:
        new_template = client.dcim.console_server_port_templates.create(**template_payload)
        client.cache.invalidate_for_objects([device_type])
    except Exception as e:
        raise ValidationError(f"NetBox API error during Console Server Port Template creation: {e}")

    return {
        "status": "success",
        "message": f"Console Server Port Template '{new_template.name}' successfully added to Device Type '{device_type_model}'.",
        "data": {
            "template_id": new_template.id,
            "template_name": new_template.name,
            "template_type": new_template.type,
            "device_type_model": device_type_model,
            "device_type_id": device_type.id,
            "description": new_template.description,
            "netbox_url": f"{client.base_url}/dcim/device-types/{device_type.id}/console-server-port-templates/"
        }
    }


@mcp_tool(category="dcim")
def netbox_add_power_outlet_template_to_device_type(
    device_type_model: str,
    name: str,
    type: str = "iec-60320-c13",
    power_port_template: Optional[str] = None,
    feed_leg: Optional[str] = None,
    description: Optional[str] = None,
    client: NetBoxClient = None,
    confirm: bool = False  
) -> Dict[str, Any]:
    """
    Add a new Power Outlet Template to an existing Device Type.

    This tool defines a standardized power outlet port for all devices of a specific model.
    Power outlet templates are essential for PDU and power distribution infrastructure.

    Args:
        device_type_model (str): The model name of the Device Type.
        name (str): The name of the power outlet (e.g., "Outlet1", "C13-01").
        type (str): The physical type of the power outlet. Defaults to "iec-60320-c13".
        power_port_template (str, optional): Name of associated power port template.
        feed_leg (str, optional): Feed leg identifier (A, B, C).
        description (str, optional): A description for the power outlet template.
        client (NetBoxClient): The active NetBox client.
        confirm (bool): Must be True to execute the operation.

    Returns:
        dict: A dictionary containing the operation result and created template data.
    """
    if not confirm:
        return {
            "status": "dry_run",
            "message": "DRY RUN: Power Outlet Template would be created. Set confirm=True to execute.",
            "would_create": {
                "device_type_model": device_type_model,
                "power_outlet_name": name,
                "power_outlet_type": type,
                "power_port_template": power_port_template,
                "feed_leg": feed_leg,
                "description": description
            }
        }

    # Find Device Type
    try:
        device_types = client.dcim.device_types.filter(model=device_type_model)
        if not device_types:
            raise NotFoundError(f"Device Type with model '{device_type_model}' not found.")
        device_type = device_types[0]
    except Exception as e:
        raise NotFoundError(f"Could not find Device Type '{device_type_model}': {e}")

    # Check for conflicts
    try:
        existing_templates = client.dcim.power_outlet_templates.filter(
            device_type_id=device_type.id,
            name=name,
            no_cache=True
        )
        if existing_templates:
            existing_template = existing_templates[0]
            logger.warning(f"Power Outlet Template conflict detected: '{name}' already exists for Device Type '{device_type_model}' (ID: {existing_template.id})")
            raise ConflictError(
                resource_type="Power Outlet Template",
                identifier=f"{name} for Device Type {device_type_model}",
                existing_id=existing_template.id
            )
    except ConflictError:
        raise
    except Exception as e:
        logger.warning(f"Could not check for existing power outlet templates: {e}")

    # Resolve power port template if specified
    power_port_template_id = None
    if power_port_template:
        try:
            power_port_templates = client.dcim.power_port_templates.filter(
                device_type_id=device_type.id,
                name=power_port_template
            )
            if power_port_templates:
                power_port_template_id = power_port_templates[0].id
                logger.info(f"Resolved power port template '{power_port_template}' to ID: {power_port_template_id}")
            else:
                logger.error(f"Power Port Template '{power_port_template}' not found for Device Type '{device_type_model}'")
                raise NotFoundError(f"Power Port Template '{power_port_template}' not found for Device Type '{device_type_model}'. Create the power port template first.")
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error resolving power port template '{power_port_template}': {e}")
            raise ValidationError(f"Failed to resolve power port template '{power_port_template}': {e}")

    # Create the template
    template_payload = {
        "device_type": device_type.id,
        "name": name,
        "type": type,
        "description": description or ""
    }
    
    if power_port_template_id:
        template_payload["power_port"] = power_port_template_id
    if feed_leg:
        template_payload["feed_leg"] = feed_leg
    
    try:
        new_template = client.dcim.power_outlet_templates.create(**template_payload)
        client.cache.invalidate_for_objects([device_type])
    except Exception as e:
        raise ValidationError(f"NetBox API error during Power Outlet Template creation: {e}")

    return {
        "status": "success",
        "message": f"Power Outlet Template '{new_template.name}' successfully added to Device Type '{device_type_model}'.",
        "data": {
            "template_id": new_template.id,
            "template_name": new_template.name,
            "template_type": new_template.type,
            "device_type_model": device_type_model,  
            "device_type_id": device_type.id,
            "description": new_template.description,
            "power_port_template": power_port_template,
            "feed_leg": feed_leg,
            "netbox_url": f"{client.base_url}/dcim/device-types/{device_type.id}/power-outlet-templates/"
        }
    }


@mcp_tool(category="dcim")
def netbox_add_front_port_template_to_device_type(
    device_type_model: str,
    name: str,
    type: str,
    rear_port_template: str,
    rear_port_position: int = 1,
    description: Optional[str] = None,
    client: NetBoxClient = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Add a new Front Port Template to an existing Device Type.

    This tool defines a standardized front-facing physical port for all devices of a specific model.
    Front port templates are essential for patch panels and fiber distribution equipment.

    Args:
        device_type_model (str): The model name of the Device Type.
        name (str): The name of the front port (e.g., "Port 1", "F1").
        type (str): The physical type of the front port (e.g., "lc", "sc", "fc").
        rear_port_template (str): Name of the associated rear port template.
        rear_port_position (int): Position on the rear port. Defaults to 1.
        description (str, optional): A description for the front port template.
        client (NetBoxClient): The active NetBox client.
        confirm (bool): Must be True to execute the operation.

    Returns:
        dict: A dictionary containing the operation result and created template data.
    """
    if not confirm:
        return {
            "status": "dry_run",
            "message": "DRY RUN: Front Port Template would be created. Set confirm=True to execute.",
            "would_create": {
                "device_type_model": device_type_model,
                "front_port_name": name,
                "front_port_type": type,
                "rear_port_template": rear_port_template,
                "rear_port_position": rear_port_position,
                "description": description
            }
        }

    # Find Device Type
    try:
        device_types = client.dcim.device_types.filter(model=device_type_model)
        if not device_types:
            raise NotFoundError(f"Device Type with model '{device_type_model}' not found.")
        device_type = device_types[0]
    except Exception as e:
        raise NotFoundError(f"Could not find Device Type '{device_type_model}': {e}")

    # Find the rear port template
    try:
        rear_port_templates = client.dcim.rear_port_templates.filter(
            device_type_id=device_type.id,
            name=rear_port_template
        )
        if not rear_port_templates:
            logger.error(f"Rear Port Template '{rear_port_template}' not found for Device Type '{device_type_model}'")
            raise NotFoundError(f"Rear Port Template '{rear_port_template}' not found for Device Type '{device_type_model}'. Create the rear port template first.")
        
        rear_port_template_obj = rear_port_templates[0]
        logger.info(f"Resolved rear port template '{rear_port_template}' to ID: {rear_port_template_obj.id}")
        
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error resolving rear port template '{rear_port_template}': {e}")
        raise ValidationError(f"Failed to resolve rear port template '{rear_port_template}': {e}")

    # Check for conflicts
    try:
        existing_templates = client.dcim.front_port_templates.filter(
            device_type_id=device_type.id,
            name=name,
            no_cache=True
        )
        if existing_templates:
            existing_template = existing_templates[0]
            logger.warning(f"Front Port Template conflict detected: '{name}' already exists for Device Type '{device_type_model}' (ID: {existing_template.id})")
            raise ConflictError(
                resource_type="Front Port Template",
                identifier=f"{name} for Device Type {device_type_model}",
                existing_id=existing_template.id
            )
    except ConflictError:
        raise
    except Exception as e:
        logger.warning(f"Could not check for existing front port templates: {e}")

    # Create the template
    template_payload = {
        "device_type": device_type.id,
        "name": name,
        "type": type,
        "rear_port": rear_port_template_obj.id,
        "rear_port_position": rear_port_position,
        "description": description or ""
    }
    
    try:
        new_template = client.dcim.front_port_templates.create(**template_payload)
        client.cache.invalidate_for_objects([device_type])
    except Exception as e:
        raise ValidationError(f"NetBox API error during Front Port Template creation: {e}")

    return {
        "status": "success",
        "message": f"Front Port Template '{new_template.name}' successfully added to Device Type '{device_type_model}'.",
        "data": {
            "template_id": new_template.id,
            "template_name": new_template.name,
            "template_type": new_template.type,
            "device_type_model": device_type_model,
            "device_type_id": device_type.id,
            "description": new_template.description,
            "rear_port_template": rear_port_template,
            "rear_port_position": rear_port_position,
            "netbox_url": f"{client.base_url}/dcim/device-types/{device_type.id}/front-port-templates/"
        }
    }


@mcp_tool(category="dcim")
def netbox_add_rear_port_template_to_device_type(
    device_type_model: str,
    name: str,
    type: str,
    positions: int = 1,
    description: Optional[str] = None,
    client: NetBoxClient = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Add a new Rear Port Template to an existing Device Type.

    This tool defines a standardized rear-facing physical port for all devices of a specific model.
    Rear port templates are essential for patch panels and fiber distribution equipment.

    Args:
        device_type_model (str): The model name of the Device Type.
        name (str): The name of the rear port (e.g., "MPO-1", "R1").
        type (str): The physical type of the rear port (e.g., "mpo", "lc", "sc").
        positions (int): Number of positions/channels on this port. Defaults to 1.
        description (str, optional): A description for the rear port template.
        client (NetBoxClient): The active NetBox client.
        confirm (bool): Must be True to execute the operation.

    Returns:
        dict: A dictionary containing the operation result and created template data.
    """
    if not confirm:
        return {
            "status": "dry_run",
            "message": "DRY RUN: Rear Port Template would be created. Set confirm=True to execute.",
            "would_create": {
                "device_type_model": device_type_model,
                "rear_port_name": name,
                "rear_port_type": type,
                "positions": positions,
                "description": description
            }
        }

    # Find Device Type
    try:
        device_types = client.dcim.device_types.filter(model=device_type_model)
        if not device_types:
            raise NotFoundError(f"Device Type with model '{device_type_model}' not found.")
        device_type = device_types[0]
    except Exception as e:
        raise NotFoundError(f"Could not find Device Type '{device_type_model}': {e}")

    # Check for conflicts
    try:
        existing_templates = client.dcim.rear_port_templates.filter(
            device_type_id=device_type.id,
            name=name,
            no_cache=True
        )
        if existing_templates:
            existing_template = existing_templates[0]
            logger.warning(f"Rear Port Template conflict detected: '{name}' already exists for Device Type '{device_type_model}' (ID: {existing_template.id})")
            raise ConflictError(
                resource_type="Rear Port Template",
                identifier=f"{name} for Device Type {device_type_model}",
                existing_id=existing_template.id
            )
    except ConflictError:
        raise
    except Exception as e:
        logger.warning(f"Could not check for existing rear port templates: {e}")

    # Create the template
    template_payload = {
        "device_type": device_type.id,
        "name": name,
        "type": type,
        "positions": positions,
        "description": description or ""
    }
    
    try:
        new_template = client.dcim.rear_port_templates.create(**template_payload)
        client.cache.invalidate_for_objects([device_type])
    except Exception as e:
        raise ValidationError(f"NetBox API error during Rear Port Template creation: {e}")

    return {
        "status": "success",
        "message": f"Rear Port Template '{new_template.name}' successfully added to Device Type '{device_type_model}'.",
        "data": {
            "template_id": new_template.id,
            "template_name": new_template.name,
            "template_type": new_template.type,
            "device_type_model": device_type_model,
            "device_type_id": device_type.id,
            "description": new_template.description,
            "positions": new_template.positions,
            "netbox_url": f"{client.base_url}/dcim/device-types/{device_type.id}/rear-port-templates/"
        }
    }


@mcp_tool(category="dcim")
def netbox_add_device_bay_template_to_device_type(
    device_type_model: str,
    name: str,
    description: Optional[str] = None,
    client: NetBoxClient = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Add a new Device Bay Template to an existing Device Type.

    This tool defines a standardized device bay for all devices of a specific model.
    Device bay templates are essential for chassis-based equipment that houses child devices.

    Args:
        device_type_model (str): The model name of the Device Type.
        name (str): The name of the device bay (e.g., "Slot 1", "Bay A").
        description (str, optional): A description for the device bay template.
        client (NetBoxClient): The active NetBox client.
        confirm (bool): Must be True to execute the operation.

    Returns:
        dict: A dictionary containing the operation result and created template data.
    """
    if not confirm:
        return {
            "status": "dry_run",
            "message": "DRY RUN: Device Bay Template would be created. Set confirm=True to execute.",
            "would_create": {
                "device_type_model": device_type_model,
                "device_bay_name": name,
                "description": description
            }
        }

    # Find Device Type
    try:
        device_types = client.dcim.device_types.filter(model=device_type_model)
        if not device_types:
            raise NotFoundError(f"Device Type with model '{device_type_model}' not found.")
        device_type = device_types[0]
    except Exception as e:
        raise NotFoundError(f"Could not find Device Type '{device_type_model}': {e}")

    # Check for conflicts
    try:
        existing_templates = client.dcim.device_bay_templates.filter(
            device_type_id=device_type.id,
            name=name,
            no_cache=True
        )
        if existing_templates:
            existing_template = existing_templates[0]
            logger.warning(f"Device Bay Template conflict detected: '{name}' already exists for Device Type '{device_type_model}' (ID: {existing_template.id})")
            raise ConflictError(
                resource_type="Device Bay Template",
                identifier=f"{name} for Device Type {device_type_model}",
                existing_id=existing_template.id
            )
    except ConflictError:
        raise
    except Exception as e:
        logger.warning(f"Could not check for existing device bay templates: {e}")

    # Create the template
    template_payload = {
        "device_type": device_type.id,
        "name": name,
        "description": description or ""
    }
    
    try:
        new_template = client.dcim.device_bay_templates.create(**template_payload)
        client.cache.invalidate_for_objects([device_type])
    except Exception as e:
        raise ValidationError(f"NetBox API error during Device Bay Template creation: {e}")

    return {
        "status": "success",
        "message": f"Device Bay Template '{new_template.name}' successfully added to Device Type '{device_type_model}'.",
        "data": {
            "template_id": new_template.id,
            "template_name": new_template.name,
            "device_type_model": device_type_model,
            "device_type_id": device_type.id,
            "description": new_template.description,
            "netbox_url": f"{client.base_url}/dcim/device-types/{device_type.id}/device-bay-templates/"
        }
    }


@mcp_tool(category="dcim")
def netbox_add_module_bay_template_to_device_type(
    device_type_model: str,
    name: str,
    position: Optional[str] = None,
    description: Optional[str] = None,
    client: NetBoxClient = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Add a new Module Bay Template to an existing Device Type.

    This tool defines a standardized module bay for all devices of a specific model.
    Module bay templates are essential for modular equipment that houses line cards and modules.

    Args:
        device_type_model (str): The model name of the Device Type.
        name (str): The name of the module bay (e.g., "Slot 1", "LC-0").
        position (str, optional): The position identifier for the module bay.
        description (str, optional): A description for the module bay template.
        client (NetBoxClient): The active NetBox client.
        confirm (bool): Must be True to execute the operation.

    Returns:
        dict: A dictionary containing the operation result and created template data.
    """
    if not confirm:
        return {
            "status": "dry_run",
            "message": "DRY RUN: Module Bay Template would be created. Set confirm=True to execute.",
            "would_create": {
                "device_type_model": device_type_model,
                "module_bay_name": name,
                "position": position,
                "description": description
            }
        }

    # Find Device Type
    try:
        device_types = client.dcim.device_types.filter(model=device_type_model)
        if not device_types:
            raise NotFoundError(f"Device Type with model '{device_type_model}' not found.")
        device_type = device_types[0]
    except Exception as e:
        raise NotFoundError(f"Could not find Device Type '{device_type_model}': {e}")

    # Check for conflicts
    try:
        existing_templates = client.dcim.module_bay_templates.filter(
            device_type_id=device_type.id,
            name=name,
            no_cache=True
        )
        if existing_templates:
            existing_template = existing_templates[0]
            logger.warning(f"Module Bay Template conflict detected: '{name}' already exists for Device Type '{device_type_model}' (ID: {existing_template.id})")
            raise ConflictError(
                resource_type="Module Bay Template",
                identifier=f"{name} for Device Type {device_type_model}",
                existing_id=existing_template.id
            )
    except ConflictError:
        raise
    except Exception as e:
        logger.warning(f"Could not check for existing module bay templates: {e}")

    # Create the template
    template_payload = {
        "device_type": device_type.id,
        "name": name,
        "description": description or ""
    }
    
    if position:
        template_payload["position"] = position
    
    try:
        new_template = client.dcim.module_bay_templates.create(**template_payload)
        client.cache.invalidate_for_objects([device_type])
    except Exception as e:
        raise ValidationError(f"NetBox API error during Module Bay Template creation: {e}")

    return {
        "status": "success",
        "message": f"Module Bay Template '{new_template.name}' successfully added to Device Type '{device_type_model}'.",
        "data": {
            "template_id": new_template.id,
            "template_name": new_template.name,
            "device_type_model": device_type_model,
            "device_type_id": device_type.id,
            "description": new_template.description,
            "position": getattr(new_template, 'position', None),
            "netbox_url": f"{client.base_url}/dcim/device-types/{device_type.id}/module-bay-templates/"
        }
    }