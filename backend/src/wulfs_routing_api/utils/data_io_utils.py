import io
import os
import pandas as pd
import tempfile
import base64

def read_table(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path)
    return pd.read_csv(path)

def write_table(df: pd.DataFrame, path: str):
    ext = os.path.splitext(path)[1].lower()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if ext in (".xlsx", ".xls"):
        df.to_excel(path, index=False)
    else:
        df.to_csv(path, index=False)


def base64_data_to_temp_file(file_name, file_content_b64, USE_HOME=True):
    """
    Decode a base64 string and save it to a temporary file.
    """
    if USE_HOME:
        home_tmp_dir = os.path.expanduser("~/tmp")
        os.makedirs(home_tmp_dir, exist_ok=True)
        temp_file_path = os.path.join(home_tmp_dir, file_name)
    else:
        import tempfile
        tmpdir = tempfile.mkdtemp()
        temp_file_path = os.path.join(tmpdir, file_name)

    # Write (overwrite if exists)
    with open(temp_file_path, "wb") as f:
        f.write(base64.b64decode(file_content_b64))

    return temp_file_path


def load_base64_to_df(base64_content: str) -> pd.DataFrame:
    """
    Load a base64-encoded file (CSV, Excel) directly into a DataFrame,
    detecting if it's text or binary automatically.
    """
    decoded_bytes = base64.b64decode(base64_content)

    # Try to decode as UTF-8 (text)
    try:
        decoded_str = decoded_bytes.decode('utf-8')
        buffer = io.StringIO(decoded_str)
        df = pd.read_csv(buffer)
        return df
    except UnicodeDecodeError:
        # If decoding fails, assume binary (e.g., Excel)
        buffer = io.BytesIO(decoded_bytes)
        try:
            df = pd.read_excel(buffer, sheet_name=0)
            return df
        except Exception as e:
            raise ValueError(f"Cannot determine file type or read file: {e}")
