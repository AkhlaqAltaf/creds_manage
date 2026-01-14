# filter_cctns.py

input_file = 'processed_creds/ePrisons.txt'  # Your input file
output_file = 'ePrisonRajasthan2.txt'                    # Output file
target_domain = 'eprisons.nic.in/Rajasthan'

with open(input_file, 'r', encoding='utf-8') as infile, \
     open(output_file, 'w', encoding='utf-8') as outfile:

    for line in infile:
        if target_domain in line:
            outfile.write(line)  # Write the entire line as-is
            # xprint(f"Copied: {line.strip()}")

print(f"\nDone! CCTNS lines saved to '{output_file}'")