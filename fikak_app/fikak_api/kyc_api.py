

import frappe
from pypika import Order
from operator import itemgetter
from itertools import groupby



@frappe.whitelist(methods=['GET'] , allow_guest=True)
def get_kyc_questions():
    kyc_questions = get_questions()
    question_grouper = itemgetter("question_id", "question_title", "question_type", "question_code" , "question_order")
    answer_grouper = itemgetter("answer_code", "answer" , "answer_order")
    questions = []
    for question_key, question_group in groupby(sorted(kyc_questions, key=itemgetter("question_order")), question_grouper):
        d = {
            "question_id": question_key[0],
            "question_title": question_key[1],
            "question_type": question_key[2],
            "question_code": question_key[3],
            "question_order" : question_key[4],
            "answers": []
        }
        for answer_key, answer_group in groupby(sorted(question_group, key=itemgetter("answer_order")), answer_grouper):
            answer = {
                "answer_code": answer_key[0],
                "answer": answer_key[1]
            }
            d.get("answers").append(answer)
        questions.append(d)
    if kyc_questions:
        return {
            "data" :{    "kyc" : kyc_questions[0]['kyc_id'],
                "kyc_title" : kyc_questions[0]['kyc_title'],
                "questions" : questions
                },
            "status": True
        }
    else:
        return {
            "data" :{},
            "status": False,
            "description": "No KYC questions found"
        }

def get_questions():
    kyc_doc = frappe.qb.DocType("KYC")
    question_doc = frappe.qb.DocType("KYC Question")
    kyc_question_item_doc = frappe.qb.DocType("KYC Question Item")
    
    answers_doc = frappe.qb.DocType("KYC Question Answer Item")
    questions_query = (
        frappe.qb.from_(kyc_doc)
        
        .left_join(kyc_question_item_doc)
        .on(kyc_doc.name == kyc_question_item_doc.parent)
        .left_join(question_doc)
        .on(question_doc.name == kyc_question_item_doc.kyc_question)

        .left_join(answers_doc)
        .on(question_doc.name == answers_doc.parent)
        .select(
            kyc_doc.name.as_("kyc_id"),
            kyc_doc.kyc_title,
            question_doc.name.as_("question_id"),
            answers_doc.idx.as_("answer_order"),
            kyc_question_item_doc.idx.as_("question_order"),
            question_doc.question_title,
            question_doc.question_type,
            question_doc.question_code,
            answers_doc.answer_code,
            answers_doc.answer



        ).where(kyc_doc.enabled == 1)
        .orderby(kyc_question_item_doc.idx, answers_doc.idx, order=Order.asc)
    )
    
    kyc_questions = questions_query.run(as_dict=True)
    return kyc_questions