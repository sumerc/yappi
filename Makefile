.PHONY: build test bump-version release

build:
	python setup.py build_ext --inplace

test:
	python run_tests.py

bump-version:
	@branch=$$(git rev-parse --abbrev-ref HEAD); \
	if [ "$$branch" != "master" ]; then echo "ERROR: must be on master branch" && exit 1; fi; \
	latest=$$(gh release view --json tagName -q .tagName 2>/dev/null || echo "v0.0.0"); \
	ver="$(VER)"; \
	if [ -z "$$ver" ]; then echo "usage: make bump-version VER=1.7.5" && exit 1; fi; \
	echo "$$ver" > VERSION; \
	claude -p "Look at the git log from tag $$latest to HEAD. Write a CHANGELOG entry for version $$ver in this exact format (no markdown headers, match the style of the existing CHANGELOG file): VERSION (YYYY-MM-DD) followed by blank line then bullet points starting with '- '. Be concise — one line per meaningful change, skip merge commits and CI-only changes. Output ONLY the changelog entry as plain text, no code fences or markdown formatting." > /tmp/yappi-changelog-entry; \
	echo "" >> /tmp/yappi-changelog-entry; \
	sed -i '' '3r /tmp/yappi-changelog-entry' CHANGELOG; \
	rm -f /tmp/yappi-changelog-entry; \
	echo "VERSION and CHANGELOG updated — review and edit as needed"

release:
	@branch=$$(git rev-parse --abbrev-ref HEAD); \
	if [ "$$branch" != "master" ]; then echo "ERROR: must be on master branch" && exit 1; fi; \
	ver=$$(cat VERSION); \
	notes=$$(awk "/^$$ver /{found=1; next} /^[0-9]+\./{if(found) exit} found{print}" CHANGELOG | sed '/^$$/d'); \
	if [ -z "$$notes" ]; then echo "ERROR: version $$ver not found in CHANGELOG — run make bump-version first" && exit 1; fi; \
	echo ""; \
	echo "$$ver Release Notes:"; \
	echo ""; \
	echo "$$notes"; \
	echo ""; \
	read -p "create release v$$ver? [y/N] " confirm; \
	case "$$confirm" in y|Y) ;; *) echo "aborted" && exit 1;; esac; \
	gh release create "v$$ver" --title "v$$ver" --notes "$$notes"
