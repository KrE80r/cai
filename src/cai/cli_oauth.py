"""
OAuth CLI commands for CAI.

Usage:
    cai auth anthropic  # Login with Claude Pro/Max subscription
    cai auth status     # Check authentication status
"""

import asyncio
import webbrowser
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.group()
def auth():
    """Manage OAuth authentication."""
    pass


@auth.command()
@click.option("--no-browser", is_flag=True, help="Don't open browser automatically")
def anthropic(no_browser: bool):
    """
    Login with Anthropic OAuth (Claude Pro/Max subscription).
    
    This allows you to use your Claude Pro/Max subscription for API access
    instead of paying per-token with an API key.
    """
    from cai.sdk.agents.oauth import (
        login_anthropic,
        save_anthropic_credentials,
        load_anthropic_credentials,
    )
    
    # Check if already authenticated
    existing = load_anthropic_credentials()
    if existing and not existing.is_expired():
        if not click.confirm("Already authenticated. Re-authenticate?", default=False):
            console.print("[green]✓ Already authenticated with Anthropic OAuth[/green]")
            return
    
    console.print(Panel(
        "[bold]Anthropic OAuth Login[/bold]\n\n"
        "This will authenticate you with your Claude Pro/Max subscription.\n"
        "You'll be redirected to claude.ai to authorize access.",
        title="🔐 Authentication",
    ))
    
    def on_auth_url(url: str):
        console.print(f"\n[bold]Authorization URL:[/bold]\n{url}\n")
        if not no_browser:
            console.print("[dim]Opening browser...[/dim]")
            webbrowser.open(url)
        else:
            console.print("[yellow]Open the URL above in your browser.[/yellow]")
    
    def on_prompt_code() -> str:
        console.print("\n[bold]After authorizing, you'll see a code.[/bold]")
        console.print("[dim]The code format is: CODE#STATE[/dim]\n")
        return click.prompt("Paste the code here")
    
    try:
        creds = asyncio.run(login_anthropic(on_auth_url, on_prompt_code))
        save_anthropic_credentials(creds)
        console.print("\n[green]✓ Successfully authenticated with Anthropic OAuth![/green]")
        console.print("[dim]Credentials saved to ~/.cai/oauth.json[/dim]")
    except Exception as e:
        console.print(f"\n[red]✗ Authentication failed: {e}[/red]")
        raise click.Abort()


@auth.command()
def status():
    """Check authentication status."""
    from cai.sdk.agents.oauth import load_anthropic_credentials
    import time
    
    creds = load_anthropic_credentials()
    
    if not creds:
        console.print("[yellow]Not authenticated with Anthropic OAuth.[/yellow]")
        console.print("[dim]Run 'cai auth anthropic' to authenticate.[/dim]")
        return
    
    if creds.is_expired():
        console.print("[yellow]⚠ Anthropic OAuth token expired.[/yellow]")
        console.print("[dim]Run 'cai auth anthropic' to re-authenticate.[/dim]")
    else:
        expires_in = (creds.expires - (time.time() * 1000)) / 1000 / 60  # minutes
        console.print("[green]✓ Authenticated with Anthropic OAuth[/green]")
        if creds.email:
            console.print(f"[dim]Email: {creds.email}[/dim]")
        console.print(f"[dim]Token expires in: {expires_in:.0f} minutes[/dim]")


@auth.command()
def refresh():
    """Manually refresh the OAuth token."""
    from cai.sdk.agents.oauth import (
        load_anthropic_credentials,
        refresh_anthropic_token,
        save_anthropic_credentials,
    )
    
    creds = load_anthropic_credentials()
    if not creds:
        console.print("[red]✗ Not authenticated. Run 'cai auth anthropic' first.[/red]")
        raise click.Abort()
    
    try:
        console.print("[dim]Refreshing token...[/dim]")
        new_creds = asyncio.run(refresh_anthropic_token(creds.refresh))
        save_anthropic_credentials(new_creds)
        console.print("[green]✓ Token refreshed successfully![/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to refresh token: {e}[/red]")
        console.print("[dim]Try re-authenticating with 'cai auth anthropic'[/dim]")
        raise click.Abort()


if __name__ == "__main__":
    auth()
