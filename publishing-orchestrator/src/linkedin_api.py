import os
import httpx
from typing import Optional, Dict, Any

LINKEDIN_API_ENABLED = os.getenv("LINKEDIN_API_ENABLED", "false").lower() == "true"
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_OWNER_URN = os.getenv("LINKEDIN_OWNER_URN")  # e.g. urn:li:person:xxxx or urn:li:organization:xxxx

class LinkedInApiError(Exception):
    pass

async def is_configured() -> bool:
    return LINKEDIN_API_ENABLED and bool(LINKEDIN_ACCESS_TOKEN and LINKEDIN_OWNER_URN)

async def _auth_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "X-Restli-Protocol-Version": "2.0.0"
    }

async def register_document_upload() -> Dict[str, Any]:
    url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    payload = {
        "registerUploadRequest": {
            "owner": LINKEDIN_OWNER_URN,
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-document"],
            "serviceRelationships": [{
                "relationshipType": "OWNER",
                "identifier": "urn:li:userGeneratedContent"
            }],
            "supportedUploadMechanism": ["SYNCHRONOUS_UPLOAD"]
        }
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, headers={**(await _auth_headers()), "Content-Type": "application/json"}, json=payload)
        if r.status_code >= 300:
            raise LinkedInApiError(f"registerUpload failed: {r.status_code} {r.text}")
        return r.json()

async def upload_document(upload_url: str, pdf_bytes: bytes) -> None:
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.put(upload_url, headers={"Content-Type": "application/pdf"}, content=pdf_bytes)
        if r.status_code >= 300:
            raise LinkedInApiError(f"upload_document failed: {r.status_code} {r.text}")

async def create_document_post(asset_urn: str, text: str, title: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
    url = "https://api.linkedin.com/v2/ugcPosts"
    payload = {
        "author": LINKEDIN_OWNER_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text or ""},
                "shareMediaCategory": "DOCUMENT",
                "media": [{
                    "status": "READY",
                    "media": asset_urn,
                    "title": {"text": title or "Presentation"},
                    "description": {"text": description or ""}
                }]
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, headers={**(await _auth_headers()), "Content-Type": "application/json"}, json=payload)
        if r.status_code >= 300:
            raise LinkedInApiError(f"create_document_post failed: {r.status_code} {r.text}")
        return r.json()

async def publish_pdf_from_url(pdf_url: str, text: str, title: Optional[str] = None, description: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Convenience helper: download PDF from provided URL, upload to LinkedIn and create a document post.
    Returns dict with keys {asset_urn, post_response} on success.
    """
    if not await is_configured():
        return None
    # Download PDF
    async with httpx.AsyncClient(timeout=60.0) as client:
        pdf_resp = await client.get(pdf_url)
        if pdf_resp.status_code != 200:
            raise LinkedInApiError(f"Failed to download PDF from {pdf_url}: {pdf_resp.status_code}")
        pdf_bytes = pdf_resp.content
    # Register upload
    reg = await register_document_upload()
    upload_mech = (reg.get("value") or {}).get("uploadMechanism") or {}
    simple = upload_mech.get("com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest") or {}
    upload_url = simple.get("uploadUrl")
    asset_urn = (reg.get("value") or {}).get("asset")
    if not upload_url or not asset_urn:
        raise LinkedInApiError("Invalid registerUpload response")
    # Upload
    await upload_document(upload_url, pdf_bytes)
    # Create post
    post_resp = await create_document_post(asset_urn, text, title=title, description=description)
    return {"asset_urn": asset_urn, "post_response": post_resp}
