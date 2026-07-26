import click
from flask import Flask
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import ROLE_ADMIN, Role, User


def register_cli_commands(app: Flask) -> None:
    @app.cli.command("create-admin")
    @click.option("--email", required=True)
    @click.option("--password", required=True)
    @click.option(
        "--if-not-exists",
        is_flag=True,
        default=False,
        help=(
            "Skip silently if an admin already exists, instead of erroring. "
            "Makes this safe to run on every container start."
        ),
    )
    def create_admin(email: str, password: str, if_not_exists: bool) -> None:
        """Bootstrap the first Admin user account.

        Creating a user normally requires being logged in as an Admin
        already (POST /api/auth/users) - this command exists purely to
        break that chicken-and-egg problem on a fresh database.
        """
        email = email.strip().lower()

        if if_not_exists:
            any_admin = (
                db.session.query(User).join(Role).filter(Role.name == ROLE_ADMIN).first()
            )
            if any_admin is not None:
                click.echo("An admin user already exists - skipping.")
                return

        existing = db.session.query(User).filter(User.email == email).first()
        if existing is not None:
            if if_not_exists:
                click.echo(f"User {email} already exists - skipping.")
                return
            click.echo(f"Error: a user with email {email} already exists.", err=True)
            raise SystemExit(1)

        role = db.session.query(Role).filter(Role.name == ROLE_ADMIN).first()
        if role is None:
            role = Role(name=ROLE_ADMIN)
            db.session.add(role)
            db.session.flush()

        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        click.echo(f"Created admin user {email} (id={user.id}).")
