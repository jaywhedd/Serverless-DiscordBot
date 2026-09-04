"""
Ed25519 signature verification for incoming Discord Interaction requests.
 
CRITICAL: This must run before ANY other logic in handler.py. This endpoint
is internet-accessible (API Gateway is public by default), so every request
must be proven to genuinely originate from Discord before we trust it,
parse it, or let it touch DynamoDB/Discord's REST API.
"""
 
 
def verify_signature(raw_body: str, signature: str, timestamp: str, public_key: str) -> bool:
    """
    Verify the Ed25519 signature Discord attaches to every interaction request.
 
    raw_body: the exact, unmodified request body string (do not parse/re-serialize
              before verifying -- even whitespace differences will break this)
    signature: value of the X-Signature-Ed25519 header
    timestamp: value of the X-Signature-Timestamp header
    public_key: this app's Discord Public Key (from ssm.get_discord_public_key())
 
    Returns True if valid, False otherwise. Uses PyNaCl's VerifyKey; catches
    BadSignatureError internally rather than letting it raise.
    """
    # TODO: implement using nacl.signing.VerifyKey
    pass
 
 
def is_timestamp_fresh(timestamp: str, max_age_seconds: int) -> bool:
    """
    Reject requests whose timestamp is older than max_age_seconds, to guard
    against replay attacks (someone capturing and re-sending an old valid
    request). Runs as a second, separate check alongside verify_signature --
    both must pass.
    """
    # TODO: implement
    pass