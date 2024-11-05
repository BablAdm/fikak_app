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

