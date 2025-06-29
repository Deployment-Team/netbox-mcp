"""
NetBox MCP Workflow Prompts

Interactive prompts that guide users through complex NetBox workflows
by orchestrating multiple tools and providing contextual guidance.
Now enhanced with Bridget persona for clear branding and user guidance.
"""

from typing import Dict, Any, List, Optional
from ..registry import mcp_prompt
from ..persona import get_bridget_introduction, get_bridget_workflow_header


@mcp_prompt(
    name="install_device_in_rack",
    description="Interactive workflow for installing a new device in a datacenter rack, guided by Bridget"
)
async def install_device_in_rack_prompt() -> Dict[str, Any]:
    """
    Interactive Device Installation Workflow - Guided by Bridget
    
    Bridget, your NetBox Infrastructure Guide, will personally walk you through
    the complete process of installing a new device in a datacenter rack.
    
    She will handle all the complex NetBox operations while keeping you informed
    about every step in the process. This ensures you always know you're working
    with NetBox MCP and have expert guidance throughout.
    
    Workflow Overview:
    1. Bridget introduces herself and the workflow
    2. Site and rack validation with live NetBox checks
    3. Device type verification and compatibility checks  
    4. Space and power capacity validation
    5. IP address allocation and network planning
    6. Device provisioning with full documentation
    7. Cable management and connection documentation
    8. Installation checklist generation and completion summary
    
    All NetBox API calls are handled by Bridget, with clear explanations
    of what's happening at each step.
    """
    
    # Bridget's introduction for this specific workflow
    bridget_intro = get_bridget_introduction(
        workflow_name="Install Device in Rack",
        user_context="Device installation in datacenter rack with full NetBox integration"
    )
    
    workflow_steps = {
        "persona_introduction": bridget_intro,
        "workflow_name": "Install Device in Rack",
        "guided_by": "Bridget - NetBox Infrastructure Guide",
        "description": "Complete device installation workflow with pre-checks and documentation",
        "netbox_integration": "Full API integration with real-time validation",
        "steps": [
            {
                "step": 1,
                "title": "Site en Rack Validatie",
                "bridget_header": get_bridget_workflow_header(1, "Site en Rack Validatie", 6),
                "bridget_guidance": "Ik ga eerst controleren of de doelsite en rack bestaan en voldoende capaciteit hebben. Dit voorkomt problemen later in het proces.",
                "description": "Bridget verifieert de target site en rack, controleert capaciteit",
                "user_inputs_required": [
                    {
                        "name": "site_name",
                        "type": "string",
                        "required": True,
                        "description": "Naam van de datacenter site (bijv. 'datacenter-1', 'Amsterdam-DC01')",
                        "bridget_help": "Ik zal alle beschikbare sites voor je ophalen uit NetBox"
                    },
                    {
                        "name": "rack_name", 
                        "type": "string",
                        "required": True,
                        "description": "Rack identifier binnen de site (bijv. 'R01', 'Rack-A-01')",
                        "bridget_help": "Na je site keuze laat ik alle beschikbare racks zien met hun capaciteit"
                    }
                ],
                "netbox_tools_executed": [
                    "netbox_get_site_info",
                    "netbox_get_rack_elevation", 
                    "netbox_get_rack_inventory"
                ],
                "bridget_validations": [
                    "Site bestaat en is actief in NetBox",
                    "Rack bestaat in de gespecificeerde site", 
                    "Rack heeft beschikbare U-space",
                    "Voldoende power capaciteit beschikbaar"
                ]
            },
            {
                "step": 2,
                "title": "Device Type and Role Selection",
                "description": "Specify the device to be installed and its intended role",
                "user_inputs_required": [
                    {
                        "name": "device_model",
                        "type": "string", 
                        "required": True,
                        "description": "Device model/type (e.g., 'Cisco Catalyst 9300', 'Dell PowerEdge R740')"
                    },
                    {
                        "name": "device_name",
                        "type": "string",
                        "required": True,
                        "description": "Unique device name (e.g., 'sw-floor1-01', 'srv-db-prod-01')"
                    },
                    {
                        "name": "device_role",
                        "type": "string",
                        "required": True,
                        "description": "Device role (e.g., 'switch', 'server', 'firewall')"
                    },
                    {
                        "name": "position_preference",
                        "type": "string",
                        "required": False,
                        "description": "Preferred rack position: 'top', 'bottom', 'middle', or specific U number",
                        "default": "bottom"
                    }
                ],
                "tools_to_execute": [
                    "netbox_list_all_device_types",
                    "netbox_list_all_device_roles"
                ],
                "validation_checks": [
                    "Device type exists in NetBox",
                    "Device role exists in NetBox",
                    "Device name is unique",
                    "Requested position is available"
                ]
            },
            {
                "step": 3,
                "title": "Network Configuration Planning",
                "description": "Allocate IP addresses and plan network connectivity",
                "user_inputs_required": [
                    {
                        "name": "management_vlan",
                        "type": "string",
                        "required": False,
                        "description": "VLAN for management interface (leave empty for auto-selection)"
                    },
                    {
                        "name": "ip_requirements",
                        "type": "integer",
                        "required": False, 
                        "description": "Number of IP addresses needed",
                        "default": 1
                    },
                    {
                        "name": "network_connections",
                        "type": "array",
                        "required": False,
                        "description": "List of network connections to document (e.g., ['uplink to sw-core-01', 'management to oob-switch'])"
                    }
                ],
                "tools_to_execute": [
                    "netbox_list_all_vlans",
                    "netbox_find_next_available_ip",
                    "netbox_list_all_prefixes"
                ],
                "validation_checks": [
                    "Management VLAN exists (if specified)",
                    "IP addresses available in selected networks",
                    "Network connectivity plan is feasible"
                ]
            },
            {
                "step": 4,
                "title": "Device Provisioning",
                "description": "Create the device in NetBox with all configurations",
                "tools_to_execute": [
                    "netbox_provision_new_device",
                    "netbox_assign_ip_to_interface"
                ],
                "automated": True,
                "description_detail": "This step automatically creates the device with all specified parameters"
            },
            {
                "step": 5,
                "title": "Cable Documentation",
                "description": "Document physical connections and cable management",
                "user_inputs_required": [
                    {
                        "name": "cable_connections",
                        "type": "array",
                        "required": False,
                        "description": "Cable connections to document (format: 'local_interface:remote_device:remote_interface')"
                    }
                ],
                "tools_to_execute": [
                    "netbox_create_cable_connection"
                ]
            },
            {
                "step": 6,
                "title": "Installation Documentation",
                "description": "Generate installation checklist and audit trail",
                "tools_to_execute": [
                    "netbox_create_journal_entry"
                ],
                "automated": True,
                "deliverables": [
                    "Installation checklist for technicians",
                    "Network configuration summary", 
                    "Cable labeling schedule",
                    "Audit trail entry"
                ]
            }
        ],
        "bridget_completion_criteria": [
            "Device succesvol aangemaakt in NetBox",
            "IP adressen gealloceerd en toegewezen",
            "Fysieke positie gereserveerd in rack", 
            "Cable verbindingen gedocumenteerd",
            "Installatie documentatie gegenereerd",
            "Journal entry aangemaakt voor audit trail"
        ],
        
        "bridget_next_steps": [
            "Fysieke installatie door datacenter technici",
            "Netwerk configuratie deployment", 
            "Device commissioning en testing",
            "Device status updaten naar 'active' na succesvolle installatie"
        ],
        
        "bridget_support": {
            "rollback_help": "Mocht er iets misgaan, dan kan ik je helpen met netbox_decommission_device om gedeeltelijk aangemaakte resources op te ruimen",
            "troubleshooting": "Bij problemen kan je me altijd vragen om specifieke NetBox checks uit te voeren",
            "documentation": "Alle acties worden gedocumenteerd in NetBox journal entries voor volledige traceerbaarheid"
        }
    }
    
    return {
        "success": True,
        "prompt_type": "interactive_workflow_with_persona",
        "persona": "Bridget - NetBox Infrastructure Guide",
        "workflow": workflow_steps,
        "estimated_duration": "15-30 minuten met Bridget's begeleiding",
        "complexity": "intermediate",
        "user_experience": "Persoonlijke begeleiding door NetBox expert",
        "branding": {
            "system": "NetBox MCP",
            "version": "v0.11.0+",
            "mascotte": "Bridget"
        },
        "prerequisites": [
            "Site en rack moeten bestaan in NetBox",
            "Device type moet gedefinieerd zijn in NetBox", 
            "IP address space moet beschikbaar zijn",
            "Gebruiker moet NetBox write permissions hebben"
        ]
    }