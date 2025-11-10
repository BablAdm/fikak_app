// Copyright (c) 2024, Waseera and contributors
// For license information, please see license.txt

frappe.ui.form.on('KYC', {
	// refresh: function(frm) {

	// }
	setup: function(frm) {
		frm.set_query("kyc_question", "questions", function (doc, cdt, cdn) {
            return {
                filters: {
                    name: ["not in", frm.doc.questions.map(p => p.kyc_question)]
                }
            };
        });
	}
});
