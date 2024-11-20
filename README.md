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


# to migrate site
 bench --site pre-eservices.waseera.sa migrate


# to forcely delete doctype and fields deleted from db
bench --site fikak_product.localhost trim-tables
 

 
#listing params template
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

#listing response template

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