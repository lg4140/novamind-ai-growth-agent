"""Safe-by-default local V3 settings; production authentication and live sending are absent."""
from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')

def flag(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ('true', '1', 'yes')

@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    db_path: Path = ROOT / 'data' / 'novamind_v4.db'
    contacts_path: Path = ROOT / 'data' / 'contacts.csv'
    output_dir: Path = ROOT / 'data' / 'generated_content'
    api_key: str = os.getenv('OPENAI_API_KEY', '')
    openai_model: str = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')
    dry_run: bool = flag('DRY_RUN', True)
    max_recipients: int = int(os.getenv('MAX_RECIPIENTS', '100'))
    contact_hmac_key: str = os.getenv('CONTACT_HMAC_KEY', 'LOCAL_DEMO_NOT_FOR_PRODUCTION')
    local_demo_review_token: str = os.getenv('LOCAL_DEMO_REVIEW_TOKEN', '')
    local_demo_reviewer_id: str = os.getenv('LOCAL_DEMO_REVIEWER_ID', 'local-reviewer')

settings = Settings()
