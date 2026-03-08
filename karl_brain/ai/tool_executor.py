"""
Dispatch des appels d'outils Claude vers les bonnes fonctions.
"""
from typing import Any, Dict

from tools.vps_tools import (
    check_health,
    deploy_application,
    get_logs,
    get_server_metrics,
    list_deployments,
    manage_container,
)
from tools.nginx_tools import configure_nginx
from tools.ssl_tools import (
    tool_ssl_check_domain,
    tool_ssl_check_expiry,
    tool_ssl_enable,
    tool_ssl_force_renew,
    tool_ssl_list_certificates,
    tool_ssl_renew_all,
    tool_ssl_revoke,
)
from tools.notification_tools import (
    tool_get_notification_config,
    tool_send_notification,
)
from tools.backup_tools import (
    tool_backup_cleanup,
    tool_backup_create,
    tool_backup_list,
    tool_backup_restore,
)
from tools.log_analysis_tools import (
    tool_analyze_logs,
    tool_compare_logs,
    tool_search_logs,
)
from tools.app_store_tools import (
    tool_get_app_info,
    tool_install_app,
    tool_list_available_apps,
)
from tools.firewall_tools import (
    tool_firewall_add_rule,
    tool_firewall_block_ip,
    tool_firewall_detect_brute_force,
    tool_firewall_list_rules,
    tool_firewall_status,
)
from tools.memory_tools import (
    tool_forget,
    tool_get_infrastructure_summary,
    tool_recall,
    tool_record_incident,
    tool_remember,
    tool_search_memory,
)
from tools.database_tools import (
    tool_database_connections,
    tool_database_dump,
    tool_database_list,
    tool_database_optimize,
    tool_database_query,
    tool_database_restore,
    tool_database_size,
    tool_database_slow_queries,
    tool_database_stats,
)
from tools.optimization_tools import (
    tool_analyze_resources,
    tool_clean_docker,
    tool_get_disk_usage_breakdown,
    tool_get_network_stats,
    tool_get_top_processes,
    tool_set_container_limits,
)
from tools.dns_tools import (
    tool_cloudflare_purge_cache,
    tool_dns_check_propagation,
    tool_dns_create_record,
    tool_dns_delete_record,
    tool_dns_list_records,
    tool_dns_lookup,
    tool_dns_toggle_proxy,
    tool_dns_update_record,
)
from tools.security_tools import (
    tool_security_check_docker,
    tool_security_check_failed_logins,
    tool_security_check_file_permissions,
    tool_security_check_open_ports,
    tool_security_check_ssh,
    tool_security_check_updates,
    tool_security_full_audit,
    tool_security_harden_ssh,
    tool_security_install_fail2ban,
    tool_security_scan_malware,
)
from tools.environment_tools import (
    tool_clone_environment,
    tool_deploy_to_environment,
    tool_get_environment_diff,
    tool_list_environments,
    tool_promote_to_production,
)
from tools.odoo_tools import (
    odoo_create_prospect,
    odoo_list_prospects,
    odoo_update_prospect,
)
from tools.analytics_tools import get_analytics


TOOL_REGISTRY: Dict[str, Any] = {
    # ── VPS base ─────────────────────────────────────────────────────────
    "deploy_application": deploy_application,
    "list_deployments": list_deployments,
    "manage_container": manage_container,
    "get_logs": get_logs,
    "get_server_metrics": get_server_metrics,
    "check_health": check_health,
    "configure_nginx": configure_nginx,
    # ── SSL ──────────────────────────────────────────────────────────────
    "enable_ssl": tool_ssl_enable,
    "ssl_list_certificates": tool_ssl_list_certificates,
    "ssl_check_expiry": tool_ssl_check_expiry,
    "ssl_check_domain": tool_ssl_check_domain,
    "ssl_renew_all": tool_ssl_renew_all,
    "ssl_force_renew": tool_ssl_force_renew,
    "ssl_revoke": tool_ssl_revoke,
    # ── Notifications ─────────────────────────────────────────────────────
    "send_notification": tool_send_notification,
    "get_notification_config": tool_get_notification_config,
    # ── Sauvegardes ───────────────────────────────────────────────────────
    "backup_create": tool_backup_create,
    "backup_list": tool_backup_list,
    "backup_restore": tool_backup_restore,
    "backup_cleanup": tool_backup_cleanup,
    # ── Logs ──────────────────────────────────────────────────────────────
    "analyze_logs": tool_analyze_logs,
    "compare_logs": tool_compare_logs,
    "search_logs": tool_search_logs,
    # ── App Store ─────────────────────────────────────────────────────────
    "list_available_apps": tool_list_available_apps,
    "get_app_info": tool_get_app_info,
    "install_app": tool_install_app,
    # ── Pare-feu ──────────────────────────────────────────────────────────
    "firewall_status": tool_firewall_status,
    "firewall_list_rules": tool_firewall_list_rules,
    "firewall_add_rule": tool_firewall_add_rule,
    "firewall_block_ip": tool_firewall_block_ip,
    "firewall_detect_brute_force": tool_firewall_detect_brute_force,
    # ── Memoire ───────────────────────────────────────────────────────────
    "remember": tool_remember,
    "recall": tool_recall,
    "forget": tool_forget,
    "search_memory": tool_search_memory,
    "get_infrastructure_summary": tool_get_infrastructure_summary,
    "record_incident": tool_record_incident,
    # ── Bases de donnees ──────────────────────────────────────────────────
    "database_list": tool_database_list,
    "database_stats": tool_database_stats,
    "database_slow_queries": tool_database_slow_queries,
    "database_connections": tool_database_connections,
    "database_query": tool_database_query,
    "database_optimize": tool_database_optimize,
    "database_dump": tool_database_dump,
    "database_restore": tool_database_restore,
    "database_size": tool_database_size,
    # ── Optimisation ──────────────────────────────────────────────────────
    "get_top_processes": tool_get_top_processes,
    "analyze_resources": tool_analyze_resources,
    "clean_docker": tool_clean_docker,
    "get_network_stats": tool_get_network_stats,
    "get_disk_usage_breakdown": tool_get_disk_usage_breakdown,
    "set_container_limits": tool_set_container_limits,
    # ── DNS / Cloudflare ──────────────────────────────────────────────────
    "dns_list_records": tool_dns_list_records,
    "dns_create_record": tool_dns_create_record,
    "dns_update_record": tool_dns_update_record,
    "dns_delete_record": tool_dns_delete_record,
    "dns_toggle_proxy": tool_dns_toggle_proxy,
    "dns_check_propagation": tool_dns_check_propagation,
    "dns_lookup": tool_dns_lookup,
    "cloudflare_purge_cache": tool_cloudflare_purge_cache,
    # ── Securite ──────────────────────────────────────────────────────────
    "security_full_audit": tool_security_full_audit,
    "security_check_open_ports": tool_security_check_open_ports,
    "security_check_docker": tool_security_check_docker,
    "security_check_file_permissions": tool_security_check_file_permissions,
    "security_check_ssh": tool_security_check_ssh,
    "security_check_failed_logins": tool_security_check_failed_logins,
    "security_check_updates": tool_security_check_updates,
    "security_harden_ssh": tool_security_harden_ssh,
    "security_install_fail2ban": tool_security_install_fail2ban,
    "security_scan_malware": tool_security_scan_malware,
    # ── Multi-environnements ──────────────────────────────────────────────
    "list_environments": tool_list_environments,
    "deploy_to_environment": tool_deploy_to_environment,
    "promote_to_production": tool_promote_to_production,
    "get_environment_diff": tool_get_environment_diff,
    "clone_environment": tool_clone_environment,
    # ── CRM Odoo ──────────────────────────────────────────────────────────
    "odoo_create_prospect": odoo_create_prospect,
    "odoo_list_prospects": odoo_list_prospects,
    "odoo_update_prospect": odoo_update_prospect,
    # ── Analytics ─────────────────────────────────────────────────────────
    "get_analytics": get_analytics,
}


async def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> Any:
    """
    Execute un outil par son nom avec les arguments fournis par Claude.

    Args:
        tool_name: Nom de l'outil (doit correspondre a TOOL_REGISTRY)
        tool_input: Arguments JSON parses

    Returns:
        Resultat de l'outil (serialisable en JSON)

    Raises:
        ValueError: Si l'outil est inconnu
    """
    if tool_name not in TOOL_REGISTRY:
        raise ValueError(
            f"Unknown tool: {tool_name!r}. Available: {sorted(TOOL_REGISTRY.keys())}"
        )

    handler = TOOL_REGISTRY[tool_name]
    return await handler(**tool_input)
