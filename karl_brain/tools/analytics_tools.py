"""
Analytics marketing — GA4 (Google Analytics 4) et Plausible.
"""
import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from core.config import get_settings

settings = get_settings()


def _period_to_dates(period: str) -> tuple[str, str]:
    """Convertit une période en dates start/end."""
    today = datetime.today()
    if period == "today":
        return today.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    elif period == "yesterday":
        d = today - timedelta(days=1)
        return d.strftime("%Y-%m-%d"), d.strftime("%Y-%m-%d")
    elif period == "7d":
        return (today - timedelta(days=7)).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    elif period == "30d":
        return (today - timedelta(days=30)).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    elif period == "90d":
        return (today - timedelta(days=90)).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    elif period == "12m":
        return (today - timedelta(days=365)).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    return (today - timedelta(days=7)).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")


async def _get_plausible(metric: str, period: str, site: Optional[str]) -> Dict[str, Any]:
    """Requête l'API Plausible."""
    if not settings.plausible_api_key:
        return {"error": "Plausible non configuré (PLAUSIBLE_API_KEY manquant)"}

    site_id = site or settings.plausible_site_id
    if not site_id:
        return {"error": "PLAUSIBLE_SITE_ID non configuré"}

    period_map = {
        "today": "day",
        "yesterday": "day",
        "7d": "7d",
        "30d": "30d",
        "90d": "month",
        "12m": "12mo",
    }
    plausible_period = period_map.get(period, "7d")

    headers = {"Authorization": f"Bearer {settings.plausible_api_key}"}
    base_url = "https://plausible.io/api/v1"

    async with httpx.AsyncClient(timeout=30) as client:
        if metric == "overview":
            resp = await client.get(
                f"{base_url}/stats/aggregate",
                params={
                    "site_id": site_id,
                    "period": plausible_period,
                    "metrics": "visitors,pageviews,bounce_rate,visit_duration",
                },
                headers=headers,
            )
            resp.raise_for_status()
            return {"provider": "plausible", "period": period, "data": resp.json()}

        elif metric == "top_pages":
            resp = await client.get(
                f"{base_url}/stats/breakdown",
                params={
                    "site_id": site_id,
                    "period": plausible_period,
                    "property": "event:page",
                    "metrics": "visitors,pageviews",
                    "limit": 10,
                },
                headers=headers,
            )
            resp.raise_for_status()
            return {"provider": "plausible", "period": period, "top_pages": resp.json()}

        elif metric == "top_sources":
            resp = await client.get(
                f"{base_url}/stats/breakdown",
                params={
                    "site_id": site_id,
                    "period": plausible_period,
                    "property": "visit:source",
                    "metrics": "visitors",
                    "limit": 10,
                },
                headers=headers,
            )
            resp.raise_for_status()
            return {"provider": "plausible", "period": period, "top_sources": resp.json()}

        else:
            # Métriques basiques
            resp = await client.get(
                f"{base_url}/stats/aggregate",
                params={
                    "site_id": site_id,
                    "period": plausible_period,
                    "metrics": metric if metric in ["visitors", "pageviews", "bounce_rate"] else "visitors,pageviews",
                },
                headers=headers,
            )
            resp.raise_for_status()
            return {"provider": "plausible", "period": period, "data": resp.json()}


async def _get_ga4(metric: str, period: str, site: Optional[str]) -> Dict[str, Any]:
    """Requête GA4 via Google Analytics Data API."""
    if not settings.ga4_property_id or not settings.ga4_credentials_json:
        return {"error": "GA4 non configuré (GA4_PROPERTY_ID ou GA4_CREDENTIALS_JSON manquant)"}

    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            RunReportRequest, DateRange, Metric, Dimension,
        )
        from google.oauth2 import service_account
        import json as _json

        credentials_info = _json.loads(settings.ga4_credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        )
        client = BetaAnalyticsDataClient(credentials=credentials)

        start_date, end_date = _period_to_dates(period)

        metric_map = {
            "pageviews": "screenPageViews",
            "sessions": "sessions",
            "users": "activeUsers",
            "bounce_rate": "bounceRate",
        }

        if metric == "overview":
            request = RunReportRequest(
                property=f"properties/{settings.ga4_property_id}",
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                metrics=[
                    Metric(name="activeUsers"),
                    Metric(name="sessions"),
                    Metric(name="screenPageViews"),
                    Metric(name="bounceRate"),
                ],
            )
        elif metric == "top_pages":
            request = RunReportRequest(
                property=f"properties/{settings.ga4_property_id}",
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                dimensions=[Dimension(name="pagePath")],
                metrics=[Metric(name="screenPageViews"), Metric(name="activeUsers")],
                limit=10,
            )
        elif metric == "top_sources":
            request = RunReportRequest(
                property=f"properties/{settings.ga4_property_id}",
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                dimensions=[Dimension(name="sessionSource")],
                metrics=[Metric(name="sessions")],
                limit=10,
            )
        else:
            ga4_metric = metric_map.get(metric, "activeUsers")
            request = RunReportRequest(
                property=f"properties/{settings.ga4_property_id}",
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                metrics=[Metric(name=ga4_metric)],
            )

        import asyncio
        response = await asyncio.get_event_loop().run_in_executor(
            None, client.run_report, request
        )

        # Formater la réponse
        rows = []
        for row in response.rows:
            row_data = {}
            for i, dim in enumerate(response.dimension_headers):
                row_data[dim.name] = row.dimension_values[i].value
            for i, met in enumerate(response.metric_headers):
                row_data[met.name] = row.metric_values[i].value
            rows.append(row_data)

        return {
            "provider": "ga4",
            "period": period,
            "metric": metric,
            "rows": rows,
        }

    except ImportError:
        return {"error": "google-analytics-data package non installé. Run: pip install google-analytics-data"}
    except Exception as e:
        return {"error": f"GA4 error: {str(e)}"}


async def get_analytics(
    metric: str,
    period: str = "7d",
    site: Optional[str] = None,
) -> Dict[str, Any]:
    """Point d'entrée principal — essaie Plausible puis GA4."""
    # Préférer Plausible si configuré
    if settings.plausible_api_key:
        return await _get_plausible(metric, period, site)
    elif settings.ga4_property_id:
        return await _get_ga4(metric, period, site)
    else:
        return {
            "error": "Aucun service analytics configuré. Définir PLAUSIBLE_API_KEY ou GA4_PROPERTY_ID dans .env",
            "tip": "Plausible est recommandé: https://plausible.io",
        }
