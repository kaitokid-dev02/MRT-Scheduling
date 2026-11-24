# Decisions

- Use Segno to generate ticket QR codes as SVG data URIs. It is a small pure-Python dependency, works without an external QR service or image library, and keeps QR generation available when the kiosk is offline.
