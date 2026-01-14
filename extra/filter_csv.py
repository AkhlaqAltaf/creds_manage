import csv

input_file = 'processed_creds/rajasthan_login_pass.txt'
output_file = 'cctns_credentials.csv'
target_domain = 'cctns.rajasthan.gov.in'

# Open CSV file and write header
with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['id', 'url', 'user', 'password', 'checked', 'working'])

    with open(input_file, 'r', encoding='utf-8') as infile:
        index = 1
        for line_num, line in enumerate(infile, 1):
            line = line.strip()
            if not line:
                continue

            if target_domain not in line:
                continue

            # Split from RIGHT using ':' → max 2 splits to get user:password
            parts = line.rsplit(':', 2)  # Split into [url..., user, password]

            if len(parts) != 3:
                print(f"[Line {line_num}] Malformed (expected user:pass): {line}")
                continue

            url_part, user, password = parts

            # Reconstruct full URL (in case there were ':' in domain/path)
            # But since domain is fixed, we rebuild safely
            full_url = f"{url_part}:{user}:{password}"  # Just for clarity
            # Actually, better: reconstruct only if needed — but we keep original logic
            # We'll use the original line up to last two ':' as URL
            url = line.rsplit(':', 2)[0]  # Everything except last two fields

            # Write to CSV
            writer.writerow([index, url, user, password, '', ''])
            print(f"[{index}] {user}:{password}")
            index += 1

print(f"\nDone! Saved {index-1} CCTNS entries to '{output_file}'")