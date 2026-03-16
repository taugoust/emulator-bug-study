from datetime import datetime
from urllib.request import urlopen
from urllib.parse import urljoin
from os import makedirs, path
from shutil import rmtree
from re import search, match
from argparse import ArgumentParser

from bs4 import BeautifulSoup

from .launchpad import process_launchpad_bug
from .thread import process_thread

def months_iterator(start, end):
    current = start
    while current <= end:
        yield current
        if current.month == 12:
            current = current.replace(year = current.year + 1, month = 1)
        else:
            current = current.replace(month = current.month + 1)

def prepare_output(ml_dir, lp_dir) -> None:
    if path.exists(ml_dir):
        rmtree(ml_dir)
    if path.exists(lp_dir):
        rmtree(lp_dir)
    makedirs(ml_dir, exist_ok = True)

def is_bug(text : str) -> bool:
    return search(r'\[[^\]]*\b(BUG|bug|Bug)\b[^\]]*\]', text)

def main():
    parser = ArgumentParser(prog='scrape-mailinglist')
    parser.add_argument('-u', '--url', required=True, help="Base URL of the mailing list archive")
    parser.add_argument('--start', required=True, help="Start month (YYYY-MM)")
    parser.add_argument('--end', required=True, help="End month (YYYY-MM)")
    parser.add_argument('-o', '--output-dir', default='.', help="Output directory (default: current directory)")
    args = parser.parse_args()

    start_date = datetime.strptime(args.start, "%Y-%m")
    end_date = datetime.strptime(args.end, "%Y-%m")
    base_url = args.url.rstrip('/')

    ml_dir = path.join(args.output_dir, "mailinglist")
    lp_dir = path.join(args.output_dir, "launchpad")

    prepare_output(ml_dir, lp_dir)

    for month in months_iterator(start_date, end_date):
        print(f"{month.strftime('%Y-%m')}")
        url = f"{base_url}/{month.strftime('%Y-%m')}/threads.html"
        html = urlopen(url).read()
        soup = BeautifulSoup(html, features = 'html5lib')

        ul = soup.body.ul
        threads = ul.find_all('li', recursive = False)
        for li in reversed(threads):
            a_tag = li.find('b').find('a')
            if not a_tag:
                continue

            text = a_tag.get_text(strip = True)
            href = a_tag.get('href')

            if not is_bug(text):
                continue

            # bug issued in launchpad
            re_match = search(r'\[Bug\s(\d+)\]', text)
            if re_match:
                process_launchpad_bug(re_match.group(1).strip(), lp_dir)
                continue

            # existing thread
            re_match = match(r'(?i)^re:\s*(.*)', text)
            if re_match:
                title_hash = str(hash(re_match.group(1).strip()))[1:9]
                out_path = path.join(ml_dir, title_hash)
                if path.exists(out_path):
                    process_thread(urljoin(url, href), out_path)
                continue

            # new thread
            title_hash = str(hash(text.strip()))[1:9]
            out_path = path.join(ml_dir, title_hash)
            if path.exists(out_path):
                print(f"ERROR: {title_hash} should not exist!")
                continue

            with open(out_path, "w") as file:
                file.write(f"{text}\n\n")
            process_thread(urljoin(url, href), out_path)

if __name__ == "__main__":
    main()
