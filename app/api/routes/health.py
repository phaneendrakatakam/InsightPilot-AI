from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine

router = APIRouter()


@router.get("/health")
def health():
    try:
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    '''
                    SELECT
                        current_database() AS database_name,
                        current_user AS database_user,
                        current_setting('transaction_read_only') AS transaction_read_only
                    '''
                )
            ).mappings().one()

        return {
            "status": "ok",
            "database": {
                "name": row["database_name"],
                "user": row["database_user"],
                "transaction_read_only": row["transaction_read_only"],
            },
        }

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable.",
        ) from exc
