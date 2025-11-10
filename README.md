## Fikak App

Finteck application for the backoffice of Waseera fikak app

#### License

MIT


## Refresh & update db 

bench --site fikak.localhost migrate

bench --site fikak.localhost migrate


#  Clear Web site cache
bench --site fikak.localhost clear-cache

# Add the fikak_app as default
cd sites/fikak.localhost
bench --site fikak.localhost set-config app fikak_app

# show the site config
bench --site fikak.localhost show-config --format text


# Clear Redis cache
bench clear-redis
=======

# Naming Format
fields naming format : 
eastlimitlength   -->   East Limit Length

doctype naming format : 
realEstateDetails  --> Real Estate Details

childtable doctypes naming :
Deed Owner -- > Deed Owner Item

variables and methods:

snake case   (test_name) 


# to migrate site
 bench --site pre-eservices.waseera.sa migrate


# to forcely delete doctype and fields deleted from db
bench --site fikak_product.localhost trim-tables
 

 
# listing params template
{
  "offset": 0,
  "page_size": 10,
  "order_direction": "", //1 or -1
  "order_field" : ""
  "global_filter": "Riadh",
  "status_filter": {
    "is_eligible": "not_eligible",
    "is_split": "inactive"
  }
}

# listing response template

{
    "meta" : {
        "size" : 1994,
        "current_page" : 1,
        "total_pages" : 140,
        "items_per_page" : 10,
    }
    "data" : [

    ],
    "status" : true,
    "message" : "succes"
}

# Response type
frappe.local.response.http_status_code = 404 (error code in case of error)
{
  "data" : [] or {} or "" or int,
  "message" : success or error string message ex : "Success Request"
  "status" : False or True
}


# install converter from hidjri to date
bench pip install convertdate

# DEV RULES
allow_guest only for true
Adding http methods for endpoints : methods=['POST']
Use queryy builder for the custom quries.
return response  { "status" : False , "message" : ""} with http code != 200 instead of throw

# Common files location rules: 

for endpoints : fikak_app/fikak_api
for external methods (integartion with payment , nafath ...) : fikak_app/external_requests
for shared methods and utils : fikak_app/utils
for controllers methods : fikak_app/controllers


Act as a senior python developer , please refactor the code to be more readable , testable , optimized and length of methods doesn't pass 15 lines