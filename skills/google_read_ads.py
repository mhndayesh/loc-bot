"""
name: read_google_ads_campaigns
description: "Fetches live campaign performance data from Google Ads using a Manager Account ID."
"""
def read_google_ads_campaigns(customer_id=""):
    import sys
    import os
    
    # Needs absolute path for google ads yaml to find its config
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ads_config_path = os.path.join(base_dir, 'google-ads.yaml')
    
    if not os.path.exists(ads_config_path):
        return f"ERROR: Missing {ads_config_path}! Google Ads requires a specific Developer Token YAML file alongside OAuth 2.0. Please create google-ads.yaml in the root project folder."
        
    if not customer_id:
        return "ERROR: Missing 'customer_id' argument. You must supply your 10-digit Google Ads account ID."

    try:
        from google.ads.googleads.client import GoogleAdsClient
        
        # We load Google Ads credentials specifically from the YAML config we enforced
        client = GoogleAdsClient.load_from_storage(ads_config_path, version="v17")
        ga_service = client.get_service("GoogleAdsService")

        query = """
            SELECT
              campaign.id,
              campaign.name,
              campaign.status,
              metrics.clicks,
              metrics.impressions,
              metrics.cost_micros
            FROM campaign
            ORDER BY campaign.id
            LIMIT 5"""

        # Removes hyphens to match required format
        customer_id = str(customer_id).replace("-", "")

        response = ga_service.search(customer_id=customer_id, query=query)
        
        output = []
        for row in response:
            campaign = row.campaign
            metrics = row.metrics
            cost_usd = metrics.cost_micros / 1000000.0 if metrics.cost_micros else 0.0
            
            output.append(f"Campaign: '{campaign.name}' (ID: {campaign.id})\nStatus: {campaign.status.name}\nClicks: {metrics.clicks}\nImpressions: {metrics.impressions}\nCost: ${cost_usd:.2f}\n---")

        if not output:
             return f"No active campaigns found for Google Ads Account {customer_id}."
             
        return "\n".join(output)
             
    except Exception as e:
        return f"An error occurred fetching Google Ads: {e}"
