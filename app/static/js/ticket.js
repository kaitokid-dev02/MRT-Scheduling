const printButton = document.getElementById('printBtn');
const qrImage = document.querySelector('.ticket__qr img');
const qrPrintError = document.getElementById('qrPrintError');

printButton?.addEventListener('click', async () => {
  if (qrImage && !qrImage.complete) {
    try {
      await qrImage.decode();
    } catch {
      if (qrPrintError) qrPrintError.hidden = false;
      return;
    }
  }

  if (qrImage && qrImage.naturalWidth === 0) {
    if (qrPrintError) qrPrintError.hidden = false;
    return;
  }

  window.print();
});
