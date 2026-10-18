import 'package:flutter/services.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';
import 'package:wasel_core/wasel_core.dart';

import 'slips.dart';

/// Prints an order's kitchen ticket and package slip through the system print
/// dialog (AirPrint on iPad, the print service on Android), sized for 80 mm
/// receipt printers. Tests swap in a fake.
class OrderPrinter {
  Future<void> printOrder(Order order, S s) async {
    final slips = OrderSlips.of(order, s, storeName: order.vendorName);
    await Printing.layoutPdf(
      name: 'wasel-order-${order.id}',
      format: PdfPageFormat.roll80,
      onLayout: (format) => buildPdf(slips, format),
    );
  }

  static Future<Uint8List> buildPdf(
    OrderSlips slips,
    PdfPageFormat format,
  ) async {
    Future<pw.Font> font(String weight) async => pw.Font.ttf(
      await rootBundle.load(
        'packages/wasel_core/assets/fonts/IBMPlexSansArabic-$weight.ttf',
      ),
    );
    final regular = await font('Regular');
    final bold = await font('Bold');
    final theme = pw.ThemeData.withFont(base: regular, bold: bold);
    final direction = slips.rtl ? pw.TextDirection.rtl : pw.TextDirection.ltr;
    final page = format.copyWith(
      marginLeft: 8,
      marginRight: 8,
      marginTop: 8,
      marginBottom: 8,
    );

    pw.Widget header(String kind) => pw.Container(
      padding: const pw.EdgeInsets.only(bottom: 4),
      decoration: const pw.BoxDecoration(
        border: pw.Border(bottom: pw.BorderSide(width: 1.5)),
      ),
      child: pw.Row(
        mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
        children: [
          pw.Text(
            'واصل',
            style: pw.TextStyle(fontSize: 16, fontWeight: pw.FontWeight.bold),
          ),
          pw.Container(
            padding: const pw.EdgeInsets.symmetric(horizontal: 6, vertical: 1),
            decoration: pw.BoxDecoration(
              border: pw.Border.all(width: 1.2),
              borderRadius: pw.BorderRadius.circular(8),
            ),
            child: pw.Text(
              kind,
              style: pw.TextStyle(fontWeight: pw.FontWeight.bold),
            ),
          ),
        ],
      ),
    );

    pw.Widget number() => pw.Text(
      slips.orderNumber,
      textDirection: pw.TextDirection.ltr,
      style: pw.TextStyle(fontSize: 30, fontWeight: pw.FontWeight.bold),
    );

    pw.Widget items({required bool large, required bool boxes}) => pw.Container(
      padding: const pw.EdgeInsets.symmetric(vertical: 4),
      decoration: const pw.BoxDecoration(
        border: pw.Border.symmetric(
          horizontal: pw.BorderSide(width: 0.8, style: pw.BorderStyle.dashed),
        ),
      ),
      child: pw.Column(
        crossAxisAlignment: pw.CrossAxisAlignment.start,
        children: [
          for (final line in slips.lines)
            pw.Padding(
              padding: const pw.EdgeInsets.symmetric(vertical: 2),
              child: pw.Row(
                crossAxisAlignment: pw.CrossAxisAlignment.start,
                children: [
                  if (boxes) ...[
                    pw.Container(
                      width: 9,
                      height: 9,
                      margin: const pw.EdgeInsets.only(top: 3),
                      decoration: pw.BoxDecoration(
                        border: pw.Border.all(width: 0.8),
                      ),
                    ),
                    pw.SizedBox(width: 5),
                  ],
                  pw.SizedBox(
                    width: 34,
                    child: pw.Text(
                      line.quantity,
                      textDirection: pw.TextDirection.ltr,
                      // Hug the reading start so names line up after a gap.
                      textAlign: slips.rtl
                          ? pw.TextAlign.right
                          : pw.TextAlign.left,
                      style: pw.TextStyle(
                        fontSize: large ? 13 : 11,
                        fontWeight: pw.FontWeight.bold,
                      ),
                    ),
                  ),
                  pw.SizedBox(width: 6),
                  pw.Expanded(
                    child: pw.Column(
                      crossAxisAlignment: pw.CrossAxisAlignment.start,
                      children: [
                        pw.Text(
                          line.name,
                          style: pw.TextStyle(
                            fontSize: large ? 13 : 11,
                            fontWeight: large
                                ? pw.FontWeight.bold
                                : pw.FontWeight.normal,
                          ),
                        ),
                        if (line.options.isNotEmpty)
                          pw.Text(
                            line.options,
                            style: const pw.TextStyle(fontSize: 10),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );

    final doc = pw.Document(
      title: 'Wasel order ${slips.orderNumber}',
      theme: theme,
    );

    // Kitchen ticket: what to cook, in large type.
    doc.addPage(
      pw.Page(
        pageFormat: page,
        textDirection: direction,
        build: (context) => pw.Column(
          crossAxisAlignment: pw.CrossAxisAlignment.start,
          children: [
            header(slips.kitchenTitle),
            pw.SizedBox(height: 4),
            pw.Text(
              slips.storeName,
              style: pw.TextStyle(fontWeight: pw.FontWeight.bold),
            ),
            number(),
            pw.Text(slips.placed),
            if (slips.readyBy.isNotEmpty)
              pw.Text(
                slips.readyBy,
                style: pw.TextStyle(fontWeight: pw.FontWeight.bold),
              ),
            pw.SizedBox(height: 4),
            items(large: true, boxes: false),
            pw.SizedBox(height: 4),
            pw.Text(slips.itemsCount, style: const pw.TextStyle(fontSize: 10)),
          ],
        ),
      ),
    );

    // Package slip: clipped to the bag, ticked off while packing.
    doc.addPage(
      pw.Page(
        pageFormat: page,
        textDirection: direction,
        build: (context) => pw.Column(
          crossAxisAlignment: pw.CrossAxisAlignment.start,
          children: [
            header(slips.packageTitle),
            number(),
            if (slips.customer.isNotEmpty) pw.Text(slips.customer),
            pw.SizedBox(height: 4),
            items(large: false, boxes: true),
            pw.SizedBox(height: 6),
            pw.Container(
              width: double.infinity,
              padding: const pw.EdgeInsets.all(5),
              decoration: pw.BoxDecoration(border: pw.Border.all(width: 1.5)),
              child: pw.Text(
                slips.payment,
                style: pw.TextStyle(fontWeight: pw.FontWeight.bold),
              ),
            ),
            pw.SizedBox(height: 4),
            pw.Text(slips.checkItems, style: const pw.TextStyle(fontSize: 10)),
            pw.SizedBox(height: 4),
            pw.Center(
              child: pw.Text(
                slips.thanks,
                style: const pw.TextStyle(fontSize: 10),
              ),
            ),
          ],
        ),
      ),
    );
    return doc.save();
  }
}

/// For tests: remembers what it was asked to print.
class FakePrinter extends OrderPrinter {
  final printed = <int>[];

  @override
  Future<void> printOrder(Order order, S s) async => printed.add(order.id);
}
