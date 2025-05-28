import html


def csv_to_html(reader):
    # Extract headers from the CSV file
    headers = reader.fieldnames

    # Start the HTML table with Bootstrap classes
    html_table = "<table class='table table-bordered table-striped'>\n"

    # Add the table headers with a distinct style
    html_table += "  <thead class='thead-dark'>\n    <tr>\n"
    for header in headers:
        html_table += f"      <th scope='col'>{html.escape(header)}</th>\n"
    html_table += "    </tr>\n  </thead>\n"

    # Add the table rows
    html_table += "  <tbody>\n"
    for row in reader:
        html_table += "    <tr>\n"
        for header in headers:
            html_table += f"      <td>{html.escape(row[header])}</td>\n"
        html_table += "    </tr>\n"
    html_table += "  </tbody>\n"

    # Close the HTML table
    html_table += "</table>"

    return html_table