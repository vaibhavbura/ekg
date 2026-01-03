
import yaml
import sys
import glob

def verify_yaml(file_path):
    print(f"Verifying {file_path}...")
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
            if not data:
                print(f"{file_path} is empty")
                return False
            
            # Simple Schema Validation
            if "docker-compose" in file_path:
                if 'services' not in data:
                    print(f"{file_path} missing 'services' key")
                    return False
            elif "teams" in file_path:
                if 'teams' not in data:
                    print(f"{file_path} missing 'teams' key")
                    return False
            
            print(f"{file_path} is valid")
            return True
    except Exception as e:
        print(f" {file_path} failed validation: {e}")
        return False

def main():
    files = glob.glob("data/*.yaml") + glob.glob("data/*.yml")
    all_pass = True
    for f in files:
        if not verify_yaml(f):
            all_pass = False
    
    sys.exit(0 if all_pass else 1)

if __name__ == "__main__":
    main()
