# Decisions

- Use Segno to generate ticket QR codes as PNG data URIs. PNG is consistently handled by browser print engines, and Segno works without an external QR service or image library, keeping QR generation available when the kiosk is offline.
