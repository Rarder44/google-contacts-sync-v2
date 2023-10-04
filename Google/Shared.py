class Shared:
    # The user field that we store a key in to uniquely identify a person across
    # accounts
    SYNC_TAG = 'SyncTag-gcs2'       #GoogleContactsSync v2

    # If modifying these scopes, delete the file token.pickle.
    SCOPES = ['https://www.googleapis.com/auth/contacts']

    # all personFields, I don't know to programmatically get these, I just got them
    # from
    # https://developers.google.com/people/api/rest/v1/people.connections/list
    all_person_fields = [
        'addresses',
        'ageRanges',
        'biographies',
        'birthdays',
        'calendarUrls',
        'clientData',
        'coverPhotos',
        'emailAddresses',
        'events',
        'externalIds',
        'genders',
        'imClients',
        'interests',
        'locales',
        'locations',
        'memberships',
        'metadata',
        'miscKeywords',
        'names',
        'nicknames',
        'occupations',
        'organizations',
        'phoneNumbers',
        'photos',
        'relations',
        'sipAddresses',
        'skills',
        'urls',
        'userDefined'
    ]

    

    all_update_person_fields = [
        'addresses',
        'biographies',
        'birthdays',
        'clientData',
        'emailAddresses',
        'events',
        'externalIds',
        'genders',
        'imClients',
        'interests',
        'locales',
        'locations',
        'memberships',
        'miscKeywords',
        'names',
        'nicknames',
        'occupations',
        'organizations',
        'phoneNumbers',
        'relations',
        'sipAddresses',
        'urls',
        'userDefined'
    ]


    group_field=["clientData","name","metadata","groupType"]


    group_id_not_to_sync=["myContacts","starred"]